"""
Settings handler - /settings command
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, update

from bot.config import settings
from bot.database import get_db, User
from bot.utils import check_user_access
from bot.ai.recommendations_provider import RecommendationsProvider

router = Router()


class GoalStates(StatesGroup):
    """FSM states for goal setting"""
    waiting_for_goal = State()
    waiting_for_medical = State()


@router.message(Command("settime"))
async def cmd_settime(message: Message):
    """Set notification time: /settime breakfast 08:30"""
    user_id = message.from_user.id
    
    # Check access
    user, has_access, error_msg = await check_user_access(user_id)
    if not has_access:
        await message.answer(error_msg)
        return
    
    # Parse command
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer(
            "❌ Неверный формат. Используй:\n"
            "<code>/settime breakfast 08:30</code>\n"
            "<code>/settime lunch 13:00</code>\n"
            "<code>/settime dinner 19:00</code>\n"
            "<code>/settime evening 21:00</code>",
            parse_mode="HTML"
        )
        return
    
    meal_type = parts[1].lower()
    time_str = parts[2]
    
    # Validate meal type
    valid_types = {
        'breakfast': 'breakfast_time',
        'lunch': 'lunch_time',
        'dinner': 'dinner_time',
        'evening': 'evening_reminder_time'
    }
    
    if meal_type not in valid_types:
        await message.answer(
            "❌ Неверный тип. Доступные: breakfast, lunch, dinner, evening"
        )
        return
    
    # Validate time format
    import re
    if not re.match(r'^([01]\d|2[0-3]):([0-5]\d)$', time_str):
        await message.answer("❌ Неверный формат времени. Используй HH:MM (например, 08:30)")
        return
    
    db_field = valid_types[meal_type]
    
    # Update in database
    async with get_db() as db:
        await db.execute(
            update(User)
            .where(User.telegram_user_id == user_id)
            .values(**{db_field: time_str})
        )
        await db.commit()
    
    meal_names = {
        'breakfast': 'Завтрак',
        'lunch': 'Обед',
        'dinner': 'Ужин',
        'evening': 'Вечернее напоминание'
    }
    
    await message.answer(f"✅ Время для '{meal_names[meal_type]}' установлено: {time_str}")


class UpdateProfile(StatesGroup):
    """States for updating profile"""
    field = State()
    value = State()


@router.message(Command("settings"))
async def cmd_settings(message: Message):
    """Handle /settings command"""
    user_id = message.from_user.id
    
    # Check access
    user, has_access, error_msg = await check_user_access(user_id)
    if not has_access:
        await message.answer(error_msg)
        return
    
    # Get user profile
    async with get_db() as db:
        result = await db.execute(
            select(User).where(User.telegram_user_id == user_id)
        )
        user = result.scalar_one_or_none()
    
    if not user:
        await message.answer("Используй /start для начала работы")
        return
    
    # Format settings
    gender_ru = "Мужской" if user.gender == "male" else "Женский"
    notifications_status = "Включены" if user.notifications_enabled else "Выключены"
    
    settings_text = (
        "⚙️ <b>Настройки профиля</b>\n\n"
        "<b>Параметры:</b>\n"
        f"  Пол: {gender_ru}\n"
        f"  Возраст: {user.age} лет\n"
        f"  Рост: {user.height} см\n\n"
        "<b>🔔 Уведомления:</b>\n"
        f"  Статус: {notifications_status}\n"
        f"  Завтрак: {user.breakfast_time}\n"
        f"  Обед: {user.lunch_time}\n"
        f"  Ужин: {user.dinner_time}\n"
        f"  Вечернее напоминание: {user.evening_reminder_time}\n\n"
        "<b>Коэффициенты расчёта:</b>\n"
        f"  Ккал на шаг: {user.step_kcal_coef}\n"
        f"  Зал (ккал/час): {user.gym_kcal_per_hour}\n"
        f"  Плавание (ккал/час): {user.swim_kcal_per_hour}\n"
        f"  Бег (ккал/час): {user.running_kcal_per_hour}\n"
        f"  Велосипед (ккал/час): {user.cycling_kcal_per_hour}\n\n"
        f"  Часовой пояс: {user.timezone}\n"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍳 Получить рекомендации по питанию", callback_data="detailed_nutrition")],
        [InlineKeyboardButton(text="💪 Получить рекомендации по тренировкам", callback_data="detailed_workout")],
        [InlineKeyboardButton(text="🔔 Включить/выключить уведомления", callback_data="toggle_notifications")],
        [InlineKeyboardButton(text="⏰ Настроить время уведомлений", callback_data="setup_notifications")],
        [InlineKeyboardButton(text="✏️ Изменить возраст", callback_data="edit_age")],
        [InlineKeyboardButton(text="✏️ Изменить рост", callback_data="edit_height")],
        [InlineKeyboardButton(text="✏️ Изменить ккал/шаг", callback_data="edit_step_coef")],
        [InlineKeyboardButton(text="✏️ Изменить ккал зал", callback_data="edit_gym_kcal")],
    ])
    
    await message.answer(settings_text, parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(F.data == "toggle_notifications")
async def callback_toggle_notifications(callback: CallbackQuery):
    """Toggle notifications on/off"""
    user_id = callback.from_user.id
    
    async with get_db() as db:
        result = await db.execute(
            select(User).where(User.telegram_user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            new_status = not user.notifications_enabled
            await db.execute(
                update(User)
                .where(User.telegram_user_id == user_id)
                .values(notifications_enabled=new_status)
            )
            await db.commit()
            
            status_text = "включены" if new_status else "выключены"
            await callback.message.answer(f"✅ Уведомления {status_text}")
    
    await callback.answer()


@router.callback_query(F.data == "setup_notifications")
async def callback_setup_notifications(callback: CallbackQuery):
    """Setup notification times"""
    user_id = callback.from_user.id
    
    async with get_db() as db:
        result = await db.execute(
            select(User).where(User.telegram_user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            text = (
                "⏰ <b>Настройка времени уведомлений</b>\n\n"
                f"Текущие настройки:\n"
                f"🍳 Завтрак: {user.breakfast_time}\n"
                f"🍽 Обед: {user.lunch_time}\n"
                f"🍴 Ужин: {user.dinner_time}\n"
                f"🌙 Вечернее напоминание: {user.evening_reminder_time}\n\n"
                "Для изменения времени отправь сообщение в формате:\n"
                "<code>/settime breakfast 08:30</code>\n"
                "<code>/settime lunch 13:00</code>\n"
                "<code>/settime dinner 19:00</code>\n"
                "<code>/settime evening 21:00</code>"
            )
            await callback.message.answer(text, parse_mode="HTML")
    
    await callback.answer()


@router.callback_query(F.data == "detailed_nutrition")
async def callback_detailed_nutrition(callback: CallbackQuery):
    """Show detailed nutrition recommendation"""
    user_id = callback.from_user.id
    
    # Check access
    user, has_access, error_msg = await check_user_access(user_id)
    if not has_access:
        await callback.answer(error_msg, show_alert=True)
        return
    
    await callback.message.answer("🥗 Генерирую подробные рекомендации по питанию...")
    
    try:
        provider = RecommendationsProvider()
        recommendation = await provider.generate_detailed_nutrition_recommendation(user)
        
        await callback.message.answer(
            f"🥗 <b>Рекомендации по питанию</b>\n\n{recommendation}",
            parse_mode="HTML"
        )
        await callback.answer()
        
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка: {str(e)}")
        await callback.answer()


@router.callback_query(F.data == "detailed_workout")
async def callback_detailed_workout(callback: CallbackQuery):
    """Show detailed workout recommendation"""
    user_id = callback.from_user.id
    
    # Check access
    user, has_access, error_msg = await check_user_access(user_id)
    if not has_access:
        await callback.answer(error_msg, show_alert=True)
        return
    
    await callback.message.answer("💪 Генерирую подробные рекомендации по тренировкам...")
    
    try:
        provider = RecommendationsProvider()
        recommendation = await provider.generate_detailed_workout_recommendation(user)
        
        await callback.message.answer(
            f"💪 <b>Рекомендации по тренировкам</b>\n\n{recommendation}",
            parse_mode="HTML"
        )
        await callback.answer()
        
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка: {str(e)}")
        await callback.answer()


@router.callback_query(F.data.startswith("edit_"))
async def callback_edit_setting(callback: CallbackQuery, state: FSMContext):
    """Handle edit setting callback"""
    field = callback.data.split("_", 1)[1]
    
    field_names = {
        'age': ('возраст', 'лет', 'age'),
        'height': ('рост', 'см', 'height'),
        'step_coef': ('коэффициент ккал/шаг', 'ккал/шаг', 'step_kcal_coef'),
        'gym_kcal': ('ккал зал (в час)', 'ккал/час', 'gym_kcal_per_hour'),
    }
    
    if field not in field_names:
        await callback.answer("Неизвестное поле")
        return
    
    field_name, unit, db_field = field_names[field]
    
    await state.update_data(edit_field=db_field, field_name=field_name, unit=unit)
    
    await callback.message.answer(
        f"✏️ Введи новое значение для <b>{field_name}</b> ({unit}):",
        parse_mode="HTML"
    )
    
    await state.set_state(UpdateProfile.value)
    await callback.answer()


@router.message(UpdateProfile.value)
async def process_setting_value(message: Message, state: FSMContext):
    """Process new setting value"""
    user_id = message.from_user.id
    
    # Check access
    user, has_access, error_msg = await check_user_access(user_id)
    if not has_access:
        await message.answer(error_msg)
        await state.clear()
        return
    
    data = await state.get_data()
    field = data['edit_field']
    field_name = data['field_name']
    
    # Parse value
    try:
        if field in ['age', 'height']:
            value = int(message.text.strip())
        else:
            value = float(message.text.replace(',', '.').strip())
        
        # Validate
        if field == 'age' and not (10 <= value <= 100):
            await message.answer("❌ Возраст должен быть в пределах 10-100 лет.")
            return
        if field == 'height' and not (100 <= value <= 250):
            await message.answer("❌ Рост должен быть в пределах 100-250 см.")
            return
        if field in ['step_kcal_coef', 'gym_kcal_per_hour'] and not (0 < value < 10000):
            await message.answer("❌ Значение должно быть положительным и разумным.")
            return
    except ValueError:
        await message.answer("❌ Не понял число. Попробуй ещё раз.")
        return
    
    # Update in database
    async with get_db() as db:
        await db.execute(
            update(User)
            .where(User.telegram_user_id == user_id)
            .values(**{field: value})
        )
        await db.commit()
    
    await message.answer(f"✅ <b>{field_name.capitalize()}</b> обновлено: {value}", parse_mode="HTML")
    await state.clear()


# Goal and medical recommendations handlers

@router.callback_query(F.data == "set_goal")
async def callback_set_goal(callback: CallbackQuery):
    """Show goal selection menu"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬇️ Похудеть", callback_data="goal_lose_weight")],
        [InlineKeyboardButton(text="➡️ Сохранить вес", callback_data="goal_maintain")],
        [InlineKeyboardButton(text="💪 Набрать мышечную массу", callback_data="goal_gain_muscle")],
        [InlineKeyboardButton(text="🔥 Подсушиться (сжечь жир)", callback_data="goal_cut")],
        [InlineKeyboardButton(text="🏋️ Стать сильнее", callback_data="goal_get_stronger")],
        [InlineKeyboardButton(text="❤️ Улучшить здоровье", callback_data="goal_health")],
        [InlineKeyboardButton(text="✏️ Ввести свою цель", callback_data="goal_custom")],
        [InlineKeyboardButton(text="◀️ Назад к настройкам", callback_data="menu_settings")],
    ])
    
    await callback.message.edit_text(
        "🎯 <b>Выбери свою цель</b>\n\n"
        "Это поможет мне давать более точные рекомендации по питанию и тренировкам:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("goal_"))
async def callback_goal_selected(callback: CallbackQuery, state: FSMContext):
    """Handle goal selection"""
    user_id = callback.from_user.id
    goal_type = callback.data.replace("goal_", "")
    
    goal_map = {
        "lose_weight": "Похудеть",
        "maintain": "Сохранить текущий вес",
        "gain_muscle": "Набрать мышечную массу",
        "cut": "Подсушиться (сжечь жир, сохранив мышцы)",
        "get_stronger": "Стать сильнее",
        "health": "Улучшить здоровье и самочувствие"
    }
    
    if goal_type == "custom":
        await callback.message.edit_text(
            "✏️ <b>Опиши свою цель</b>\n\n"
            "Например:\n"
            "• Подготовиться к марафону\n"
            "• Улучшить гибкость\n"
            "• Набрать 5 кг мышечной массы\n\n"
            "Напиши свою цель одним сообщением:",
            parse_mode="HTML"
        )
        await state.set_state(GoalStates.waiting_for_goal)
        await callback.answer()
        return
    
    goal_text = goal_map.get(goal_type, "Не указана")
    
    # Update goal in database
    async with get_db() as db:
        await db.execute(
            update(User)
            .where(User.telegram_user_id == user_id)
            .values(goal=goal_text)
        )
        await db.commit()
    
    await callback.message.edit_text(
        f"✅ <b>Цель установлена!</b>\n\n"
        f"Твоя цель: {goal_text}\n\n"
        f"Теперь рекомендации будут учитывать эту цель! 🎯",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад к настройкам", callback_data="menu_settings")]
        ])
    )
    await callback.answer()


@router.message(GoalStates.waiting_for_goal)
async def process_custom_goal(message: Message, state: FSMContext):
    """Process custom goal input"""
    user_id = message.from_user.id
    goal_text = message.text.strip()
    
    if len(goal_text) < 5:
        await message.answer("❌ Опиши цель подробнее (минимум 5 символов)")
        return
    
    if len(goal_text) > 500:
        await message.answer("❌ Слишком длинное описание. Максимум 500 символов.")
        return
    
    # Update goal in database
    async with get_db() as db:
        await db.execute(
            update(User)
            .where(User.telegram_user_id == user_id)
            .values(goal=goal_text)
        )
        await db.commit()
    
    await message.answer(
        f"✅ <b>Цель установлена!</b>\n\n"
        f"Твоя цель: {goal_text}\n\n"
        f"Теперь рекомендации будут учитывать эту цель! 🎯",
        parse_mode="HTML"
    )
    await state.clear()


@router.callback_query(F.data == "set_medical")
async def callback_set_medical(callback: CallbackQuery, state: FSMContext):
    """Request medical recommendations"""
    await callback.message.edit_text(
        "🏥 <b>Врачебные рекомендации</b>\n\n"
        "Если у тебя есть медицинские рекомендации от врача, "
        "противопоказания или ограничения - опиши их.\n\n"
        "<b>Например:</b>\n"
        "• Аллергия на молочные продукты\n"
        "• Проблемы с коленями - избегать бега\n"
        "• Диабет - контролировать углеводы\n"
        "• Вегетарианская диета\n\n"
        "Напиши свои рекомендации одним сообщением или нажми Пропустить:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_medical")],
            [InlineKeyboardButton(text="◀️ Назад к настройкам", callback_data="menu_settings")]
        ])
    )
    await state.set_state(GoalStates.waiting_for_medical)
    await callback.answer()


@router.callback_query(F.data == "skip_medical")
async def callback_skip_medical(callback: CallbackQuery, state: FSMContext):
    """Skip medical recommendations"""
    user_id = callback.from_user.id
    
    # Clear medical recommendations
    async with get_db() as db:
        await db.execute(
            update(User)
            .where(User.telegram_user_id == user_id)
            .values(medical_recommendations=None)
        )
        await db.commit()
    
    await callback.message.edit_text(
        "✅ Врачебные рекомендации пропущены.\n\n"
        "Ты всегда можешь добавить их позже через настройки профиля.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад к настройкам", callback_data="menu_settings")]
        ])
    )
    await state.clear()
    await callback.answer()


@router.message(GoalStates.waiting_for_medical)
async def process_medical_recommendations(message: Message, state: FSMContext):
    """Process medical recommendations input"""
    user_id = message.from_user.id
    medical_text = message.text.strip()
    
    if len(medical_text) < 5:
        await message.answer("❌ Опиши рекомендации подробнее (минимум 5 символов) или нажми Пропустить")
        return
    
    if len(medical_text) > 1000:
        await message.answer("❌ Слишком длинное описание. Максимум 1000 символов.")
        return
    
    # Update medical recommendations in database
    async with get_db() as db:
        await db.execute(
            update(User)
            .where(User.telegram_user_id == user_id)
            .values(medical_recommendations=medical_text)
        )
        await db.commit()
    
    await message.answer(
        f"✅ <b>Врачебные рекомендации сохранены!</b>\n\n"
        f"Твои рекомендации: {medical_text}\n\n"
        f"Я буду учитывать их при составлении рекомендаций! 🏥",
        parse_mode="HTML"
    )
    await state.clear()
