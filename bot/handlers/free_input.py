"""
Free input handler - parse free-form text with AI estimation
"""
from datetime import date, datetime
import json
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.sql import and_

from bot.config import settings
from bot.database import get_db, User, DayEntry, InputMode, WorkoutType
from bot.parsers import FreeTextParser
from bot.calculations import update_day_entry_calculations
from bot.ai import OllamaProvider

logger = logging.getLogger(__name__)
router = Router()


class FreeInput(StatesGroup):
    """States for free input confirmation"""
    confirm = State()


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
        
        ai_provider = OllamaProvider()
        
        if not await ai_provider.is_available():
            await message.answer(
                "⚠️ AI-сервис недоступен. Укажите калории вручную:\n"
                "Ккал: 850"
            )
            return
        
        ai_estimate = await ai_provider.estimate_food(food_data['description'])
        
        if ai_estimate:
            # Update AI usage counter
            async with get_db() as db:
                user.ai_requests_today += 1
                user.last_ai_request = datetime.utcnow()
                await db.commit()
            
            # Update parsed data with AI estimate
            parsed_data['food']['kcal'] = ai_estimate.total_calories
            parsed_data['food']['protein'] = ai_estimate.total_protein
            parsed_data['food']['fat'] = ai_estimate.total_fat
            parsed_data['food']['carbs'] = ai_estimate.total_carbs
            parsed_data['food']['ai_estimated'] = True
            parsed_data['food']['ai_model'] = ai_estimate.model_used
            parsed_data['food']['ai_confidence'] = ai_estimate.confidence
            parsed_data['food']['ai_items'] = [
                {
                    'name': item.name,
                    'calories': item.calories,
                    'protein': item.protein,
                    'fat': item.fat,
                    'carbs': item.carbs
                }
                for item in ai_estimate.items
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
    """Confirm and save free input"""
    data = await state.get_data()
    parsed = data['parsed_data']
    raw_text = data['raw_text']
    user_db_id = data['user_db_id']
    
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
        
        # Calculate fields
        entry = update_day_entry_calculations(entry, user)
        
        await db.commit()
    
    await callback.message.edit_text("✅ Данные сохранены!")
    await callback.message.answer(
        "Используй /today для просмотра сводки."
    )
    
    await state.clear()
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
