"""
Free input handler - parse free-form text with AI estimation
"""
from datetime import date, datetime, time, timedelta
import json
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.sql import and_

from bot.config import settings
from bot.database import get_db, User, DayEntry, MealEntry, InputMode, WorkoutType, MealType
from bot.parsers import FreeTextParser
from bot.calculations import update_day_entry_calculations
from bot.ai.smart_provider import SmartAIProvider

logger = logging.getLogger(__name__)
router = Router()


class FreeInput(StatesGroup):
    """States for free input confirmation"""
    confirm = State()
    meal_type_selection = State()
    meal_time_selection = State()


def extract_date_from_text(text: str) -> date:
    """
    Извлекает дату из текста, распознавая временные маркеры
    Returns: date объект (today, yesterday, etc.)
    """
    if not text:
        return date.today()
    
    text_lower = text.lower()
    
    # Вчера
    if any(word in text_lower for word in ['вчера', 'yesterday']):
        return date.today() - timedelta(days=1)
    
    # Позавчера
    if any(word in text_lower for word in ['позавчера', 'позовчера']):
        return date.today() - timedelta(days=2)
    
    # Сегодня (явное указание)
    if any(word in text_lower for word in ['сегодня', 'today']):
        return date.today()
    
    # По умолчанию - сегодня
    return date.today()

@router.message(F.text, F.text.len() > 20)
async def handle_free_text(message: Message, state: FSMContext):
    """Handle free-form text input with AI estimation"""
    user_id = message.from_user.id
    
    # Get user
    async with get_db() as db:
        result = await db.execute(
            select(User).where(User.telegram_user_id == user_id)
        )
        user = result.scalar_one_or_none()
    
    if not user:
        await message.answer("Отправь /start для начала работы")
        return
    
    # Check access
    if not user.is_allowed and not user.is_owner:
        await message.answer(
            "❌ У вас нет доступа к боту.\n"
            "Свяжитесь с владельцем для получения доступа."
        )
        return
    
    # Parse the text
    parser = FreeTextParser(timezone=user.timezone)
    parsed_data, missing_fields = parser.parse(message.text)
    
    # Улучшаем распознавание даты, если парсер не нашел
    if 'date' not in parsed_data or parsed_data.get('date') == date.today():
        detected_date = extract_date_from_text(message.text)
        if detected_date != date.today():
            parsed_data['date'] = detected_date
    
    # Check if food needs AI estimation
    food_data = parsed_data.get('food', {})
    needs_ai = food_data and 'description' in food_data and 'kcal' not in food_data
    
    ai_estimate = None
    if needs_ai:
        # Check AI limit
        if user.ai_requests_today >= user.ai_requests_limit:
            await message.answer(
                f"⚠️ Достигнут дневной лимит AI-запросов ({user.ai_requests_limit}/день)\n\n"
                f"Укажите калории вручную, например:\n"
                f"Ккал: 850"
            )
            return
        
        # Try AI estimation
        await message.answer("🤖 Оцениваю калорийность с помощью AI...")
        
        ai_provider = SmartAIProvider()
        
        estimate = await ai_provider.estimate_food(food_data['description'])
        
        if not estimate:
            await message.answer(
                "⚠️ AI-сервис недоступен. Укажите калории вручную:\n"
                "Ккал: 850"
            )
            return
        
        estimate = await ai_provider.estimate_food(food_data['description'])
        
        if estimate:
            # Update AI usage counter
            async with get_db() as db:
                user.ai_requests_today += 1
                user.last_ai_request = datetime.utcnow()
                await db.commit()
            
            # Update parsed data with AI estimate
            parsed_data['food']['kcal'] = estimate.total_calories
            parsed_data['food']['protein'] = estimate.total_protein
            parsed_data['food']['fat'] = estimate.total_fat
            parsed_data['food']['carbs'] = estimate.total_carbs
            parsed_data['food']['ai_estimated'] = True
            parsed_data['food']['ai_model'] = estimate.model_used
            parsed_data['food']['ai_confidence'] = getattr(estimate, 'confidence', 'medium')
            parsed_data['food']['ai_items'] = [
                {
                    'name': item.name,
                    'calories': item.calories,
                    'protein': item.protein,
                    'fat': item.fat,
                    'carbs': item.carbs
                }
                for item in estimate.items
            ]
        else:
            await message.answer(
                "⚠️ Не удалось оценить калории. Укажите вручную:\n"
                "Ккал: 850"
            )
            return
    
    # Store parsed data
    await state.update_data(
        user_db_id=user.id,
        parsed_data=parsed_data,
        missing_fields=missing_fields,
        raw_text=message.text,
        ai_estimate=ai_estimate
    )
    
    # Format preview
    preview = _format_parsed_preview(parsed_data, missing_fields, ai_estimate)
    
    # Buttons
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data="free_confirm"),
            InlineKeyboardButton(text="❌ Отменить", callback_data="free_cancel")
        ]
    ])
    
    await message.answer(
        f"📝 <b>Распознал следующие данные:</b>\n\n{preview}",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    
    await state.set_state(FreeInput.confirm)


@router.callback_query(FreeInput.confirm, F.data == "free_confirm")
async def confirm_free_input(callback: CallbackQuery, state: FSMContext):
    """Confirm and save free input or ask for meal type"""
    data = await state.get_data()
    parsed = data['parsed_data']
    
    # Check if food was detected
    if 'food' in parsed:
        # Check if meal_type already detected in text
        if 'meal_type' in parsed['food']:
            # Meal type already recognized, ask if user wants to specify time (optional)
            meal_type_names = {
                'breakfast': '🍳 Завтрак',
                'lunch': '🍲 Обед',
                'dinner': '🍽 Ужин',
                'snack': '🍪 Перекус'
            }
            meal_name = meal_type_names.get(parsed['food']['meal_type'], 'Приём пищи')
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🕐 Указать время", callback_data="food_meal_set_time")],
                [InlineKeyboardButton(text="⏭ Пропустить", callback_data="food_meal_skip")]
            ])
            
            await callback.message.edit_text(
                f"✅ {meal_name} распознан!\n\n"
                f"💡 Хотите указать точное время приёма пищи?\n"
                f"(Это поможет более точному анализу, но не обязательно)",
                reply_markup=keyboard
            )
            await state.set_state(FreeInput.meal_type_selection)
            return
        
        # Ask for meal type
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🍳 Завтрак", callback_data="food_meal_breakfast"),
                InlineKeyboardButton(text="🍽 Обед", callback_data="food_meal_lunch"),
            ],
            [
                InlineKeyboardButton(text="🍴 Ужин", callback_data="food_meal_dinner"),
                InlineKeyboardButton(text="🥤 Перекус", callback_data="food_meal_snack"),
            ],
            [
                InlineKeyboardButton(text="⏰ Указать время", callback_data="food_meal_set_time"),
            ],
            [
                InlineKeyboardButton(text="⏭ Пропустить", callback_data="food_meal_skip"),
            ]
        ])
        
        await callback.message.edit_text(
            "🍽 <b>Тип приема пищи</b>\n\n"
            "Выбери, когда ты это ел:",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
        await state.set_state(FreeInput.meal_type_selection)
        await callback.answer()
        return
    
    # No food - save directly
    await _save_entry(callback, state)
    await callback.answer()


@router.callback_query(FreeInput.confirm, F.data == "free_cancel")
async def cancel_free_input(callback: CallbackQuery, state: FSMContext):
    """Cancel free input"""
    await callback.message.edit_text("❌ Отменено. Попробуй ещё раз.")
    await state.clear()
    await callback.answer()


def _format_parsed_preview(parsed: dict, missing: list, ai_estimate=None) -> str:
    """Format parsed data preview with AI estimation"""
    preview = ""
    
    if 'date' in parsed:
        preview += f"📅 Дата: {parsed['date'].strftime('%d.%m.%Y')}\n"
    
    if 'weight' in parsed:
        preview += f"⚖️ Вес: {parsed['weight']} кг\n"
    
    if 'waist' in parsed:
        preview += f"📏 Талия: {parsed['waist']} см\n"
    
    if 'sleep' in parsed:
        sleep = parsed['sleep']
        preview += f"😴 Сон: {sleep['hours']:.1f} ч\n"
    
    if 'steps' in parsed:
        preview += f"🚶 Шаги: {parsed['steps']:,}\n"
    
    if 'workout' in parsed:
        workout = parsed['workout']
        workout_names = {
            WorkoutType.GYM: "Зал",
            WorkoutType.SWIMMING: "Плавание",
            WorkoutType.RUNNING: "Бег",
            WorkoutType.CYCLING: "Велосипед",
            WorkoutType.OTHER: "Другое"
        }
        workout_name = workout_names.get(workout['type'], str(workout['type']))
        preview += f"💪 Тренировка: {workout_name}"
        if 'minutes' in workout:
            preview += f" ({workout['minutes']} мин)"
        preview += "\n"
    
    if 'food' in parsed:
        food = parsed['food']
        preview += "\n🍽 <b>Еда:</b>\n"
        
        if food.get('ai_estimated'):
            preview += f"🤖 <i>Оценка AI ({food.get('ai_model', 'AI')}):</i>\n"
            
            # Show individual items if available
            if 'ai_items' in food:
                for item in food['ai_items']:
                    preview += f"  • {item['name']}: {item['calories']:.0f} ккал\n"
                    preview += f"    Б: {item['protein']:.0f}г, Ж: {item['fat']:.0f}г, У: {item['carbs']:.0f}г\n"
            
            preview += f"\n  <b>Итого: {food['kcal']:.0f} ккал</b>\n"
            preview += f"  БЖУ: {food['protein']:.0f}/{food['fat']:.0f}/{food['carbs']:.0f}\n"
            
            confidence_pct = int(food.get('ai_confidence', 0.75) * 100)
            preview += f"  📊 Точность оценки: ~{confidence_pct}%\n"
        elif 'kcal' in food:
            preview += f"  Калории: {food['kcal']:.0f} ккал\n"
            if 'protein' in food:
                preview += f"  БЖУ: {food['protein']:.0f}/{food['fat']:.0f}/{food['carbs']:.0f}\n"
        
        if 'description' in food:
            desc = food['description']
            if len(desc) > 100:
                desc = desc[:100] + "..."
            preview += f"  Описание: {desc}\n"
    
    if missing:
        preview += f"\n⚠️ Не распознано: {', '.join(missing)}"
    
    return preview


def _merge_parsed_data_to_entry(entry: DayEntry, parsed: dict, raw_text: str):
    """Merge parsed data into existing entry"""
    # Update only non-null fields
    if 'weight' in parsed:
        entry.weight = parsed['weight']
    
    if 'waist' in parsed:
        entry.waist = parsed['waist']
    
    if 'sleep' in parsed:
        entry.sleep_hours = parsed['sleep']['hours']
    
    if 'steps' in parsed:
        entry.steps = parsed['steps']
    
    if 'workout' in parsed:
        workout = parsed['workout']
        entry.workout_type = workout['type']
        entry.workout_minutes = workout.get('minutes')
        entry.workout_kcal_manual = workout.get('kcal_manual')
    
    if 'food' in parsed:
        food = parsed['food']
        if 'kcal' in food:
            entry.kcal_eaten = food['kcal']
        if 'protein' in food:
            entry.protein = food['protein']
            entry.fat = food['fat']
            entry.carbs = food['carbs']
        
        # Store AI metadata
        if food.get('ai_estimated'):
            entry.food_ai_estimated = True
            entry.food_ai_model = food.get('ai_model')
            entry.food_ai_confidence = food.get('ai_confidence')
            if 'ai_items' in food:
                entry.food_items_json = json.dumps(food['ai_items'], ensure_ascii=False)
    
    # Append to raw text
    if entry.raw_text:
        entry.raw_text += f"\n---\n{raw_text}"
    else:
        entry.raw_text = raw_text


def _create_entry_from_parsed(user_id: int, entry_date: date, parsed: dict, raw_text: str) -> DayEntry:
    """Create new DayEntry from parsed data"""
    entry = DayEntry(
        user_id=user_id,
        entry_date=entry_date,
        raw_text=raw_text
    )
    
    # Set fields from parsed data
    if 'weight' in parsed:
        entry.weight = parsed['weight']
    
    if 'waist' in parsed:
        entry.waist = parsed['waist']
    
    if 'sleep' in parsed:
        entry.sleep_hours = parsed['sleep']['hours']
    
    if 'steps' in parsed:
        entry.steps = parsed['steps']
    
    if 'workout' in parsed:
        workout = parsed['workout']
        entry.workout_type = workout['type']
        entry.workout_minutes = workout.get('minutes')
        entry.workout_kcal_manual = workout.get('kcal_manual')
    
    if 'food' in parsed:
        food = parsed['food']
        if 'kcal' in food:
            entry.kcal_eaten = food['kcal']
        if 'protein' in food:
            entry.protein = food['protein']
            entry.fat = food['fat']
            entry.carbs = food['carbs']
    
    return entry


# Meal type selection handlers

@router.callback_query(FreeInput.meal_type_selection, F.data.startswith("food_meal_"))
async def handle_meal_type_selection(callback: CallbackQuery, state: FSMContext):
    """Handle meal type selection"""
    meal_type_str = callback.data.replace("food_meal_", "")
    
    if meal_type_str == "skip":
        # Save without meal type
        await state.update_data(meal_type=None, meal_time=None)
        await _save_entry(callback, state)
        await callback.answer()
        return
    
    if meal_type_str == "set_time":
        # Handle time setting - moved to separate handler
        await handle_meal_set_time(callback, state)
        return
    
    # Map to MealType enum
    meal_type_map = {
        "breakfast": MealType.BREAKFAST,
        "lunch": MealType.LUNCH,
        "dinner": MealType.DINNER,
        "snack": MealType.SNACK
    }
    
    meal_type = meal_type_map.get(meal_type_str)
    if not meal_type:
        await callback.answer("❌ Неверный тип приема пищи", show_alert=True)
        return
    
    # Save meal type
    await state.update_data(meal_type=meal_type, meal_time=None)
    
    # Save entry
    await _save_entry(callback, state)
    await callback.answer()


@router.callback_query(FreeInput.meal_type_selection, F.data == "food_meal_set_time")
async def handle_meal_set_time(callback: CallbackQuery, state: FSMContext):
    """Ask user to specify meal time"""
    await callback.message.edit_text(
        "⏰ <b>Укажи время приема пищи</b>\n\n"
        "Напиши время в формате HH:MM\n"
        "Например: 08:30 или 14:00",
        parse_mode="HTML"
    )
    
    await state.set_state(FreeInput.meal_time_selection)
    await callback.answer()


@router.message(FreeInput.meal_time_selection, F.text)
async def handle_meal_time_input(message: Message, state: FSMContext):
    """Process meal time input"""
    time_text = message.text.strip()
    
    # Parse time
    try:
        time_obj = datetime.strptime(time_text, "%H:%M").time()
        meal_time_str = time_obj.strftime("%H:%M")
        
        # Save time
        await state.update_data(meal_time=meal_time_str)
        
        # Check if meal_type was already recognized
        data = await state.get_data()
        parsed = data.get('parsed_data', {})
        
        if 'food' in parsed and 'meal_type' in parsed['food']:
            # Meal type already recognized, save directly
            meal_type_map = {
                "breakfast": MealType.BREAKFAST,
                "lunch": MealType.LUNCH,
                "dinner": MealType.DINNER,
                "snack": MealType.SNACK
            }
            meal_type = meal_type_map.get(parsed['food']['meal_type'])
            await state.update_data(meal_type=meal_type)
            
            await message.answer(f"✅ Время установлено: {meal_time_str}")
            await _save_entry_from_message(message, state)
            return
        
        # Meal type not recognized, ask for it
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🍳 Завтрак", callback_data="food_meal_breakfast"),
                InlineKeyboardButton(text="🍽 Обед", callback_data="food_meal_lunch"),
            ],
            [
                InlineKeyboardButton(text="🍴 Ужин", callback_data="food_meal_dinner"),
                InlineKeyboardButton(text="🥤 Перекус", callback_data="food_meal_snack"),
            ],
            [
                InlineKeyboardButton(text="⏭ Пропустить", callback_data="food_meal_skip"),
            ]
        ])
        
        await message.answer(
            f"✅ Время установлено: {meal_time_str}\n\n"
            "🍽 Теперь выбери тип приема пищи:",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
        await state.set_state(FreeInput.meal_type_selection)
        
    except ValueError:
        await message.answer(
            "❌ Неверный формат времени. Используй HH:MM\n"
            "Например: 08:30 или 14:00"
        )


async def _save_entry_from_message(message: Message, state: FSMContext):
    """Save entry from message (not callback)"""
    data = await state.get_data()
    parsed = data['parsed_data']
    raw_text = data['raw_text']
    user_db_id = data['user_db_id']
    meal_type = data.get('meal_type')
    meal_time = data.get('meal_time')
    
    async with get_db() as db:
        # Get user
        result = await db.execute(select(User).where(User.id == user_db_id))
        user = result.scalar_one()
        
        # Get entry date
        entry_date = parsed.get('date', date.today())
        
        # Check if entry exists
        result = await db.execute(
            select(DayEntry).where(
                and_(
                    DayEntry.user_id == user_db_id,
                    DayEntry.entry_date == entry_date
                )
            )
        )
        entry = result.scalar_one_or_none()
        
        if entry:
            # Update existing entry (merge data)
            _merge_parsed_data_to_entry(entry, parsed, raw_text)
        else:
            # Create new entry
            entry = _create_entry_from_parsed(user_db_id, entry_date, parsed, raw_text)
            db.add(entry)
        
        # If food was detected and meal_type is set, create MealEntry
        if 'food' in parsed and meal_type:
            food = parsed['food']
            
            meal_entry = MealEntry(
                user_id=user_db_id,
                entry_date=entry_date,
                meal_type=meal_type,
                meal_time=meal_time,
                kcal=food.get('kcal'),
                protein=food.get('protein'),
                fat=food.get('fat'),
                carbs=food.get('carbs'),
                food_description=food.get('description'),
                raw_text=raw_text,
                food_ai_estimated=food.get('ai_estimated', False),
                food_ai_model=food.get('ai_model'),
                food_ai_confidence=food.get('ai_confidence'),
                food_items_json=json.dumps(food.get('ai_items', []), ensure_ascii=False) if 'ai_items' in food else None
            )
            
            db.add(meal_entry)
        
        # Calculate fields
        entry = update_day_entry_calculations(entry, user)
        
        await db.commit()
    
    meal_type_emoji = {
        MealType.BREAKFAST: "🍳",
        MealType.LUNCH: "🍽",
        MealType.DINNER: "🍴",
        MealType.SNACK: "🥤"
    }
    
    meal_type_names = {
        MealType.BREAKFAST: "Завтрак",
        MealType.LUNCH: "Обед",
        MealType.DINNER: "Ужин",
        MealType.SNACK: "Перекус"
    }
    
    message_text = "✅ Данные сохранены!"
    
    if meal_type and meal_time:
        emoji = meal_type_emoji.get(meal_type, "🍽")
        name = meal_type_names.get(meal_type, "Приём пищи")
        message_text += f"\n{emoji} {name} в {meal_time}"
    elif meal_type:
        emoji = meal_type_emoji.get(meal_type, "🍽")
        name = meal_type_names.get(meal_type, "Приём пищи")
        message_text += f"\n{emoji} {name}"
    
    await message.answer(message_text, parse_mode="HTML")
    await state.clear()


async def _save_entry(callback: CallbackQuery, state: FSMContext):
    """Save entry with optional meal information"""
    data = await state.get_data()
    parsed = data['parsed_data']
    raw_text = data['raw_text']
    user_db_id = data['user_db_id']
    meal_type = data.get('meal_type')
    meal_time = data.get('meal_time')
    ai_estimate = data.get('ai_estimate')
    
    async with get_db() as db:
        # Get user
        result = await db.execute(select(User).where(User.id == user_db_id))
        user = result.scalar_one()
        
        # Get entry date
        entry_date = parsed.get('date', date.today())
        
        # Check if entry exists
        result = await db.execute(
            select(DayEntry).where(
                and_(
                    DayEntry.user_id == user_db_id,
                    DayEntry.entry_date == entry_date
                )
            )
        )
        entry = result.scalar_one_or_none()
        
        if entry:
            # Update existing entry (merge data)
            _merge_parsed_data_to_entry(entry, parsed, raw_text)
        else:
            # Create new entry
            entry = _create_entry_from_parsed(user_db_id, entry_date, parsed, raw_text)
            db.add(entry)
        
        # If food was detected and meal_type is set, create MealEntry
        if 'food' in parsed and meal_type:
            food = parsed['food']
            
            meal_entry = MealEntry(
                user_id=user_db_id,
                entry_date=entry_date,
                meal_type=meal_type,
                meal_time=meal_time,
                kcal=food.get('kcal'),
                protein=food.get('protein'),
                fat=food.get('fat'),
                carbs=food.get('carbs'),
                food_description=food.get('description'),
                raw_text=raw_text,
                food_ai_estimated=food.get('ai_estimated', False),
                food_ai_model=food.get('ai_model'),
                food_ai_confidence=food.get('ai_confidence'),
                food_items_json=json.dumps(food.get('ai_items', []), ensure_ascii=False) if 'ai_items' in food else None
            )
            
            db.add(meal_entry)
        
        # Calculate fields
        entry = update_day_entry_calculations(entry, user)
        
        await db.commit()
    
    meal_type_emoji = {
        MealType.BREAKFAST: "🍳",
        MealType.LUNCH: "🍽",
        MealType.DINNER: "🍴",
        MealType.SNACK: "🥤"
    }
    
    message_text = "✅ Данные сохранены!"
    if meal_type:
        emoji = meal_type_emoji.get(meal_type, "🍽")
        type_name = {
            MealType.BREAKFAST: "Завтрак",
            MealType.LUNCH: "Обед",
            MealType.DINNER: "Ужин",
            MealType.SNACK: "Перекус"
        }.get(meal_type, "Прием пищи")
        
        message_text = f"✅ Данные сохранены!\n\n{emoji} {type_name}"
        if meal_time:
            message_text += f" в {meal_time}"
    
    await callback.message.edit_text(message_text)
    await callback.message.answer("Используй /today для просмотра сводки.")
    
    await state.clear()
