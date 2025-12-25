"""
Photo input handler - анализ фото еды
"""
import logging
import re
from datetime import date, timedelta
from typing import Optional
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import os

from bot.ai.gemini_vision_provider import GeminiVisionProvider
from bot.database.db import get_db
from bot.database.models import User
from sqlalchemy import select

logger = logging.getLogger(__name__)
router = Router()


class PhotoInputState(StatesGroup):
    """Состояния для обработки фото"""
    waiting_for_clarification = State()  # Ожидание ответов на вопросы
    waiting_for_confirmation = State()  # Ожидание подтверждения
    waiting_for_meal_time = State()  # Ожидание времени приема пищи


def extract_portion_info(text: str) -> Optional[str]:
    """Извлечь информацию о размере порции из текста"""
    if not text:
        return None
    
    text_lower = text.lower()
    
    # Полный список возможных вариантов
    portions = {
        r'\bкусоч(ек|ка|ку)\b': 'маленький кусочек',
        r'\bполпорции\b|\bпол порции\b|\bполовин(а|у)\b': 'половина порции',
        r'\bнемного\b|\bчуть-чуть\b|\bмаленьк(ая|ую) порц': 'небольшая порция',
        r'\bбольш(ая|ую) порц|\bдвойн(ая|ую)\b': 'большая порция',
        r'\bцел(ый|ую|ая)\b': 'целое блюдо',
        r'\b2 куска\b|\bдва куска\b': '2 кусочка',
        r'\b3 куска\b|\bтри куска\b': '3 кусочка',
    }
    
    import re
    for pattern, label in portions.items():
        if re.search(pattern, text_lower):
            return label
    
    return None


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


@router.message(F.photo)
async def handle_photo(message: Message, state: FSMContext):
    """
    Обработка фото еды
    Бот сам понимает что пришло фото и анализирует
    """
    # Получаем пользователя
    async with get_db() as session:
        result = await session.execute(
            select(User).where(User.telegram_user_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer("❌ Сначала нажмите /start")
            return
        
        # Проверяем доступ (white-list)
        if not user.is_allowed and not user.is_owner:
            await message.answer(
                "🔒 У вас нет доступа к боту.\n"
                "Попросите владельца добавить вас: /allow"
            )
            return
    
    # Отправляем статус
    status_msg = await message.answer("🤖 Анализирую фото еды...")
    
    try:
        # Получаем API ключ из переменных окружения
        api_key = os.getenv('GEMINI_API_KEY')
        
        if not api_key:
            await status_msg.edit_text(
                "❌ API ключ Gemini не настроен.\n\n"
                "Чтобы использовать распознавание по фото:\n"
                "1. Получите бесплатный API ключ: https://makersuite.google.com/app/apikey\n"
                "2. Добавьте в .env файл: GEMINI_API_KEY=ваш_ключ\n"
                "3. Перезапустите бота\n\n"
                "⚠️ Внимание: Фото будет отправлено на сервера Google для анализа."
            )
            return
        
        # Создаем провайдер
        vision_provider = GeminiVisionProvider(api_key=api_key)
        
        # Скачиваем фото
        photo = message.photo[-1]  # Самое большое разрешение
        file = await message.bot.get_file(photo.file_id)
        photo_bytes = await message.bot.download_file(file.file_path)
        photo_data = photo_bytes.read()
        
        # Извлекаем дату из подписи к фото (caption)
        photo_caption = message.caption or ""
        entry_date = extract_date_from_text(photo_caption)
        
        # Извлекаем информацию о размере порции
        portion_info = extract_portion_info(photo_caption)
        additional_context = f"Размер порции: {portion_info}" if portion_info else None
        
        # Анализируем
        estimate = await vision_provider.analyze_food_photo(photo_data, additional_context=additional_context)
        
        if not estimate:
            await status_msg.edit_text(
                "❌ Не удалось распознать еду на фото.\n"
                "Попробуйте:\n"
                "• Сделать фото ближе\n"
                "• Улучшить освещение\n"
                "• Или ввести текстом: Еда: название блюда"
            )
            return
        
        # Формируем ответ
        confidence_emoji = {
            "low": "🟡",
            "medium": "🟢",
            "high": "🟢"
        }
        
        response = f"📸 **Я вижу на фото:**\n\n"
        
        # Список блюд
        for item in estimate.detected_items:
            response += f"• {item}\n"
        
        response += f"\n{estimate.description}\n\n"
        
        # Показываем дату, если это не сегодня
        if entry_date != date.today():
            days_diff = (date.today() - entry_date).days
            if days_diff == 1:
                date_label = "📆 Вчера"
            elif days_diff == 2:
                date_label = "📆 Позавчера"
            else:
                date_label = f"📆 {entry_date.strftime('%d.%m.%Y')}"
            response += f"{date_label}\n\n"
        
        # Оценка
        response += f"**Оценка калорий:** ~{estimate.calories:.0f} ккал\n"
        response += f"**БЖУ:** {estimate.protein:.0f}/{estimate.fat:.0f}/{estimate.carbs:.0f}г\n"
        response += f"**Уверенность:** {confidence_emoji.get(estimate.confidence_level, '🟡')} {estimate.confidence_level} ({estimate.confidence*100:.0f}%)\n\n"
        
        # Предположения
        if estimate.assumptions:
            response += "**Я предположил:**\n"
            for assumption in estimate.assumptions:
                response += f"• {assumption}\n"
            response += "\n"
        
        # Сохраняем данные в state (включая дату)
        await state.update_data(
            photo_estimate=estimate,
            clarification_answers={},
            entry_date=entry_date  # Сохраняем распознанную дату
        )
        
        # Если есть уточняющие вопросы
        if estimate.clarification_questions:
            response += "**Уточните пожалуйста:**\n"
            
            # Показываем первый вопрос
            first_question = estimate.clarification_questions[0]
            response += f"\n{first_question.question}"
            
            # Добавляем вариант "Без соуса" / "Ничего" если это вопрос о дополнениях
            options = list(first_question.options)
            if "соус" in first_question.question.lower() or "добав" in first_question.question.lower():
                # Проверяем, нет ли уже варианта "нет/без/ничего" в списке
                has_none_option = any(
                    any(word in opt.lower() for word in ["нет", "без", "ничего", "none", "no"])
                    for opt in options
                )
                if not has_none_option:
                    options.append("🚫 Без соуса / Ничего")
            
            # Создаем кнопки с вариантами (по 2 в ряд)
            buttons = []
            row = []
            for i, option in enumerate(options):
                row.append(InlineKeyboardButton(
                    text=option,
                    callback_data=f"clarify_{first_question.field}_{i}"
                ))
                if len(row) == 2:  # По 2 кнопки в ряд
                    buttons.append(row)
                    row = []
            if row:  # Добавляем последнюю строку если есть
                buttons.append(row)
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            
            # Сохраняем расширенный список опций для правильной обработки
            await state.update_data(
                current_question_options=options
            )
            
            await state.update_data(
                current_question_index=0,
                total_questions=len(estimate.clarification_questions),
                current_question_options=options
            )
            await state.set_state(PhotoInputState.waiting_for_clarification)
            
            await status_msg.edit_text(response, reply_markup=keyboard, parse_mode="Markdown")
        else:
            # Нет вопросов - сразу подтверждение
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Записать", callback_data="photo_confirm"),
                    InlineKeyboardButton(text="✏️ Изменить", callback_data="photo_edit")
                ],
                [InlineKeyboardButton(text="❌ Отменить", callback_data="photo_cancel")]
            ])
            
            await state.set_state(PhotoInputState.waiting_for_confirmation)
            await status_msg.edit_text(response, reply_markup=keyboard, parse_mode="Markdown")
    
    except Exception as e:
        logger.error(f"Ошибка обработки фото: {e}", exc_info=True)
        await status_msg.edit_text(
            f"❌ Ошибка при анализе фото:\n{str(e)}\n\n"
            "Попробуйте еще раз или введите текстом."
        )


@router.callback_query(F.data.startswith("clarify_"), PhotoInputState.waiting_for_clarification)
async def handle_clarification(callback: CallbackQuery, state: FSMContext):
    """Обработка ответов на уточняющие вопросы"""
    await callback.answer()
    
    # Парсим ответ: clarify_field_index
    # Формат: clarify_{field}_{index}
    # Проблема: field может содержать подчеркивания (например "portion_size")
    # Поэтому берем последнюю часть как индекс, а все остальное - как field
    parts = callback.data.split("_")
    option_index = int(parts[-1])  # Последняя часть - всегда индекс
    field = "_".join(parts[1:-1])  # Все между "clarify" и индексом - это field
    
    # Получаем данные
    data = await state.get_data()
    estimate = data['photo_estimate']
    current_q_index = data['current_question_index']
    total_questions = data['total_questions']
    clarification_answers = data.get('clarification_answers', {})
    current_options = data.get('current_question_options', [])
    
    # Сохраняем ответ (используем расширенный список опций)
    question = estimate.clarification_questions[current_q_index]
    if option_index < len(current_options):
        selected_option = current_options[option_index]
    else:
        # Fallback на оригинальный список
        selected_option = question.options[option_index] if option_index < len(question.options) else "Не указано"
    clarification_answers[field] = selected_option
    
    # Следующий вопрос?
    next_q_index = current_q_index + 1
    
    if next_q_index < total_questions:
        # Есть еще вопросы
        next_question = estimate.clarification_questions[next_q_index]
        
        # Экранируем специальные символы в selected_option для Markdown
        safe_option = selected_option.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')
        
        response = f"Отлично! *{field}*: {safe_option}\n\n"
        response += f"*Следующий вопрос ({next_q_index + 1}/{total_questions}):*\n"
        response += next_question.question
        
        # Добавляем вариант "Без соуса" / "Ничего" если это вопрос о дополнениях
        options = list(next_question.options)
        if "соус" in next_question.question.lower() or "добав" in next_question.question.lower():
            # Проверяем, нет ли уже варианта "нет/без/ничего" в списке
            has_none_option = any(
                any(word in opt.lower() for word in ["нет", "без", "ничего", "none", "no"])
                for opt in options
            )
            if not has_none_option:
                options.append("🚫 Без соуса / Ничего")
        
        # Создаем кнопки (по 2 в ряд)
        buttons = []
        row = []
        for i, option in enumerate(options):
            row.append(InlineKeyboardButton(
                text=option,
                callback_data=f"clarify_{next_question.field}_{i}"
            ))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        
        await state.update_data(
            current_question_index=next_q_index,
            clarification_answers=clarification_answers,
            current_question_options=options
        )
        
        await callback.message.edit_text(response, reply_markup=keyboard, parse_mode="Markdown")
    
    else:
        # Все вопросы заданы - пересчитываем с учетом ответов
        # TODO: Здесь можно переспросить AI с дополнительным контекстом
        # Пока просто показываем финальное подтверждение
        
        response = "<b>Финальная оценка:</b>\n\n"
        response += f"📊 Калории: ~{estimate.calories:.0f} ккал\n"
        response += f"БЖУ: {estimate.protein:.0f}/{estimate.fat:.0f}/{estimate.carbs:.0f}г\n\n"
        response += "<b>Ваши уточнения:</b>\n"
        for field, answer in clarification_answers.items():
            # Экранируем только HTML символы
            safe_answer = answer.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            response += f"• {field}: {safe_answer}\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Записать", callback_data="photo_confirm"),
                InlineKeyboardButton(text="✏️ Изменить", callback_data="photo_edit")
            ],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="photo_cancel")]
        ])
        
        await state.set_state(PhotoInputState.waiting_for_confirmation)
        await callback.message.edit_text(response, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "photo_confirm", PhotoInputState.waiting_for_confirmation)
async def confirm_photo_entry(callback: CallbackQuery, state: FSMContext):
    """Спросить тип приема пищи перед сохранением"""
    await callback.answer()
    
    # Ask for meal type
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🍳 Завтрак", callback_data="photo_meal_breakfast"),
            InlineKeyboardButton(text="🍽 Обед", callback_data="photo_meal_lunch"),
        ],
        [
            InlineKeyboardButton(text="🍴 Ужин", callback_data="photo_meal_dinner"),
            InlineKeyboardButton(text="🥤 Перекус", callback_data="photo_meal_snack"),
        ],
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="photo_meal_skip")]
    ])
    
    await callback.message.edit_text(
        "🍽 <b>Какой это был прием пищи?</b>",
        parse_mode="HTML",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "photo_cancel")
async def cancel_photo_entry(callback: CallbackQuery, state: FSMContext):
    """Отмена записи"""
    await callback.answer()
    await callback.message.edit_text("❌ Отменено")
    await state.clear()


@router.callback_query(F.data == "photo_edit")
async def edit_photo_entry(callback: CallbackQuery, state: FSMContext):
    """Ручное редактирование"""
    await callback.answer()
    await callback.message.edit_text(
        "✏️ Хорошо, введите калории вручную:\n\n"
        "Формат: Еда: название, калории ккал"
    )
    await state.clear()


@router.callback_query(F.data.startswith("photo_meal_"))
async def handle_photo_meal_type(callback: CallbackQuery, state: FSMContext):
    """Handle meal type selection for photo"""
    await callback.answer()
    
    meal_type_str = callback.data.replace("photo_meal_", "")
    
    if meal_type_str == "skip":
        # Save without meal type
        await _save_photo_entry(callback, state, meal_type=None)
        return
    
    # Map to MealType
    from bot.database.models import MealType
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
    
    # Save meal type and ask for time (optional)
    await state.update_data(meal_type=meal_type)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🕐 Указать время", callback_data="photo_set_time")],
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="photo_time_skip")]
    ])
    
    meal_names = {
        MealType.BREAKFAST: "Завтрак",
        MealType.LUNCH: "Обед",
        MealType.DINNER: "Ужин",
        MealType.SNACK: "Перекус"
    }
    
    await callback.message.edit_text(
        f"✅ {meal_names[meal_type]} выбран!\n\n"
        f"💡 Хотите указать точное время приема пищи?\n"
        f"(Это поможет более точному анализу, но не обязательно)",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "photo_set_time")
async def handle_photo_set_time(callback: CallbackQuery, state: FSMContext):
    """Ask user to specify meal time"""
    from datetime import date, timedelta
    await callback.answer()
    
    # Get entry date from state to show it
    data = await state.get_data()
    entry_date = data.get('entry_date', date.today())
    
    # Format date label
    date_info = ""
    if entry_date != date.today():
        days_diff = (date.today() - entry_date).days
        if days_diff == 1:
            date_info = f"📆 Дата: <b>вчера</b> ({entry_date.strftime('%d.%m.%Y')})\n\n"
        elif days_diff == 2:
            date_info = f"📆 Дата: <b>позавчера</b> ({entry_date.strftime('%d.%m.%Y')})\n\n"
        else:
            date_info = f"📆 Дата: <b>{entry_date.strftime('%d.%m.%Y')}</b>\n\n"
    
    await callback.message.edit_text(
        f"⏰ <b>Укажи время приема пищи</b>\n\n"
        f"{date_info}"
        f"Напиши время в формате HH:MM\n"
        f"Например: 08:30 или 19:45",
        parse_mode="HTML"
    )
    await state.set_state(PhotoInputState.waiting_for_meal_time)


@router.message(PhotoInputState.waiting_for_meal_time, F.text)
async def handle_photo_meal_time_input(message: Message, state: FSMContext):
    """Process meal time input for photo"""
    from datetime import datetime, date, timedelta
    time_text = message.text.strip()
    
    # Check if user is trying to specify date (вчера/позавчера)
    date_from_text = extract_date_from_text(time_text)
    if date_from_text != date.today():
        # User mentioned yesterday/day before - update date in state
        await state.update_data(entry_date=date_from_text)
        
        date_label = ""
        if date_from_text == date.today() - timedelta(days=1):
            date_label = "вчера"
        elif date_from_text == date.today() - timedelta(days=2):
            date_label = "позавчера"
        
        await message.answer(
            f"📆 Дата изменена на <b>{date_label}</b> ({date_from_text.strftime('%d.%m.%Y')})\n\n"
            "⏰ Теперь укажи время в формате HH:MM\n"
            "Например: 08:30 или 19:45",
            parse_mode="HTML"
        )
        return
    
    # Parse time
    try:
        time_obj = datetime.strptime(time_text, "%H:%M").time()
        meal_time_str = time_obj.strftime("%H:%M")
        
        # Get entry date from state
        data = await state.get_data()
        entry_date = data.get('entry_date', date.today())
        
        # Check if time is not in future
        now = datetime.now()
        entry_datetime = datetime.combine(entry_date, time_obj)
        
        if entry_datetime > now:
            current_date_str = entry_date.strftime('%d.%m.%Y')
            await message.answer(
                f"⚠️ Нельзя указать время в будущем!\n"
                f"Дата: {current_date_str}\n"
                f"Введенное время: {meal_time_str}\n\n"
                "💡 Если это было вчера - напиши 'вчера', и я обновлю дату.",
                parse_mode="HTML"
            )
            return
        
        # Save time and entry
        await state.update_data(meal_time=meal_time_str)
        
        meal_type = data.get('meal_type')
        
        await message.answer(f"✅ Время установлено: {meal_time_str}")
        await _save_photo_entry_from_message(message, state, meal_type=meal_type, meal_time=meal_time_str)
        
    except ValueError:
        await message.answer(
            "❌ Неверный формат времени. Используй HH:MM\n"
            "Например: 08:30 или 14:00"
        )


@router.callback_query(F.data == "photo_time_skip")
async def handle_photo_time_skip(callback: CallbackQuery, state: FSMContext):
    """Skip time input and save"""
    await callback.answer()
    data = await state.get_data()
    meal_type = data.get('meal_type')
    await _save_photo_entry(callback, state, meal_type=meal_type, meal_time=None)


async def _save_or_update_meal_entry(session, user, entry_date, day_entry, meal_type, meal_time, estimate, food_description):
    """Save new meal or update existing if same time exists"""
    from sqlalchemy import and_
    from datetime import datetime
    from bot.database.models import MealEntry
    
    # Check if meal with same time already exists (without meal_type check to avoid type issues)
    existing_meal = None
    if meal_time:
        # Only check by time, user and date - skip meal_type to avoid enum comparison issues
        result = await session.execute(
            select(MealEntry).where(
                and_(
                    MealEntry.user_id == user.id,
                    MealEntry.entry_date == entry_date,
                    MealEntry.meal_time == meal_time
                )
            )
        )
        existing_meal = result.scalar_one_or_none()
    
    if existing_meal:
        # Update existing meal - add to it
        existing_meal.kcal = (existing_meal.kcal or 0) + estimate.calories
        existing_meal.protein = (existing_meal.protein or 0) + estimate.protein
        existing_meal.fat = (existing_meal.fat or 0) + estimate.fat
        existing_meal.carbs = (existing_meal.carbs or 0) + estimate.carbs
        # Append food description
        if existing_meal.food_description:
            existing_meal.food_description += ", " + food_description
        else:
            existing_meal.food_description = food_description
        existing_meal.updated_at = datetime.utcnow()
        return existing_meal, True  # True = updated existing
    else:
        # Create new meal entry
        meal_entry = MealEntry(
            user_id=user.id,
            day_entry_id=day_entry.id,
            entry_date=entry_date,
            meal_type=meal_type,
            meal_time=meal_time,
            kcal=estimate.calories,
            protein=estimate.protein,
            fat=estimate.fat,
            carbs=estimate.carbs,
            food_description=food_description
        )
        session.add(meal_entry)
        return meal_entry, False  # False = created new


async def _save_photo_entry(callback: CallbackQuery, state: FSMContext, meal_type=None, meal_time=None):
    """Save photo entry to database"""
    data = await state.get_data()
    estimate = data['photo_estimate']
    clarification_answers = data.get('clarification_answers', {})
    
    # Получаем пользователя
    async with get_db() as session:
        result = await session.execute(
            select(User).where(User.telegram_user_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.message.edit_text("❌ Ошибка: пользователь не найден")
            await state.clear()
            return
        
        # Получаем entry_date из state или используем сегодня
        from datetime import date, datetime, time as dt_time
        from bot.database.models import DayEntry, MealEntry
        import json
        
        entry_date = data.get('entry_date', date.today())
        result = await session.execute(
            select(DayEntry).where(
                DayEntry.user_id == user.id,
                DayEntry.entry_date == entry_date
            )
        )
        day_entry = result.scalar_one_or_none()
        
        if not day_entry:
            day_entry = DayEntry(
                user_id=user.id,
                entry_date=entry_date
            )
            session.add(day_entry)
            await session.flush()  # Получаем id
        
        # Создаем или обновляем запись о приеме пищи
        food_description = ", ".join(estimate.detected_items)
        
        # Validate meal_time format if provided
        validated_time = None
        if meal_time:
            try:
                # Validate format but keep as string for VARCHAR column
                datetime.strptime(meal_time, "%H:%M")
                validated_time = meal_time
            except ValueError:
                pass
        
        # Save or update meal entry
        meal_entry, was_updated = await _save_or_update_meal_entry(
            session, user, entry_date, day_entry, meal_type, 
            validated_time, estimate, food_description
        )
        
        # Обновляем общие данные дня
        day_entry.kcal_eaten = (day_entry.kcal_eaten or 0) + estimate.calories
        day_entry.protein = (day_entry.protein or 0) + estimate.protein
        day_entry.fat = (day_entry.fat or 0) + estimate.fat
        day_entry.carbs = (day_entry.carbs or 0) + estimate.carbs
        
        # Метаданные AI
        day_entry.food_ai_estimated = True
        day_entry.food_ai_model = estimate.model_used
        day_entry.food_ai_confidence = estimate.confidence
        day_entry.food_items_json = json.dumps(estimate.detected_items, ensure_ascii=False)
        
        # Метаданные фото
        day_entry.photo_analyzed = True
        day_entry.photo_description = estimate.description
        day_entry.food_description = food_description
        
        if clarification_answers:
            day_entry.photo_clarifications_json = json.dumps(clarification_answers, ensure_ascii=False)
        
        # Инкрементируем счетчик AI запросов
        user.ai_requests_today += 1
        user.last_ai_request = datetime.utcnow()
        
        await session.commit()
    
    # Format response
    meal_type_emojis = {
        None: "📸",
        "breakfast": "🍳",
        "lunch": "🍲",
        "dinner": "🍽",
        "snack": "🥤"
    }
    
    from bot.database.models import MealType
    meal_type_str = meal_type.value if meal_type else None
    emoji = meal_type_emojis.get(meal_type_str, "📸")
    
    time_info = f" в {meal_time}" if meal_time else ""
    
    await callback.message.edit_text(
        f"✅ <b>Записано!</b>\n\n"
        f"{emoji} {food_description}{time_info}\n\n"
        f"📊 Калории: +{estimate.calories:.0f} ккал\n"
        f"БЖУ: Б:{estimate.protein:.0f} Ж:{estimate.fat:.0f} У:{estimate.carbs:.0f}г\n\n"
        f"Посмотреть сводку: /today",
        parse_mode="HTML"
    )
    
    await state.clear()


async def _save_photo_entry_from_message(message: Message, state: FSMContext, meal_type=None, meal_time=None):
    """Save photo entry from message (not callback)"""
    data = await state.get_data()
    estimate = data['photo_estimate']
    clarification_answers = data.get('clarification_answers', {})
    
    # Получаем пользователя
    async with get_db() as session:
        result = await session.execute(
            select(User).where(User.telegram_user_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer("❌ Ошибка: пользователь не найден")
            await state.clear()
            return
        
        # Получаем или создаем запись за сегодня
        from datetime import date, datetime, time as dt_time
        from bot.database.models import DayEntry, MealEntry
        import json
        
        today = date.today()
        entry_date = data.get('entry_date', today)
        result = await session.execute(
            select(DayEntry).where(
                DayEntry.user_id == user.id,
                DayEntry.entry_date == entry_date
            )
        )
        day_entry = result.scalar_one_or_none()
        
        if not day_entry:
            day_entry = DayEntry(
                user_id=user.id,
                entry_date=entry_date
            )
            session.add(day_entry)
            await session.flush()
        
        # Создаем или обновляем запись о приеме пищи
        food_description = ", ".join(estimate.detected_items)
        
        # Validate meal_time format if provided
        validated_time = None
        if meal_time:
            try:
                # Validate format but keep as string for VARCHAR column
                datetime.strptime(meal_time, "%H:%M")
                validated_time = meal_time
            except ValueError:
                pass
        
        # Save or update meal entry
        meal_entry, was_updated = await _save_or_update_meal_entry(
            session, user, entry_date, day_entry, meal_type, 
            validated_time, estimate, food_description
        )
        session.add(meal_entry)
        
        # Обновляем общие данные дня
        day_entry.kcal_eaten = (day_entry.kcal_eaten or 0) + estimate.calories
        day_entry.protein = (day_entry.protein or 0) + estimate.protein
        day_entry.fat = (day_entry.fat or 0) + estimate.fat
        day_entry.carbs = (day_entry.carbs or 0) + estimate.carbs
        
        # Метаданные AI
        day_entry.food_ai_estimated = True
        day_entry.food_ai_model = estimate.model_used
        day_entry.food_ai_confidence = estimate.confidence
        day_entry.food_items_json = json.dumps(estimate.detected_items, ensure_ascii=False)
        
        # Метаданные фото
        day_entry.photo_analyzed = True
        day_entry.photo_description = estimate.description
        day_entry.food_description = food_description
        
        if clarification_answers:
            day_entry.photo_clarifications_json = json.dumps(clarification_answers, ensure_ascii=False)
        
        # Инкрементируем счетчик AI запросов
        user.ai_requests_today += 1
        user.last_ai_request = datetime.utcnow()
        
        await session.commit()
    
    # Format response
    meal_type_emojis = {
        None: "📸",
        "breakfast": "🍳",
        "lunch": "🍲",
        "dinner": "🍽",
        "snack": "🥤"
    }
    
    from bot.database.models import MealType
    meal_type_str = meal_type.value if meal_type else None
    emoji = meal_type_emojis.get(meal_type_str, "📸")
    
    time_info = f" в {meal_time}" if meal_time else ""
    
    await message.answer(
        f"✅ <b>Записано!</b>\n\n"
        f"{emoji} {food_description}{time_info}\n\n"
        f"📊 Калории: +{estimate.calories:.0f} ккал\n"
        f"БЖУ: Б:{estimate.protein:.0f} Ж:{estimate.fat:.0f} У:{estimate.carbs:.0f}г\n\n"
        f"Посмотреть сводку: /today",
        parse_mode="HTML"
    )
    
    await state.clear()


@router.callback_query(F.data == "photo_cancel")
async def cancel_photo_entry(callback: CallbackQuery, state: FSMContext):
    """Отмена записи"""
    await callback.answer()
