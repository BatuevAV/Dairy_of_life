"""
Main menu handler with organized submenus
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select

from bot.database import get_db, User
from bot.utils import check_user_access
from bot.keyboards import get_main_keyboard

router = Router()


@router.message(F.text == "📋 Меню")
@router.message(Command("menu"))
async def cmd_menu(message: Message):
    """Show main menu"""
    user_id = message.from_user.id
    
    # Check access
    user, has_access, error_msg = await check_user_access(user_id)
    if not has_access:
        await message.answer(error_msg)
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu_settings")],
        [InlineKeyboardButton(text="📊 Сводка и статистика", callback_data="menu_stats")],
        [InlineKeyboardButton(text="🍽 Рекомендации питания", callback_data="menu_nutrition")],
        [InlineKeyboardButton(text="📝 Добавить запись", callback_data="menu_add")],
    ])
    
    await message.answer(
        "🏠 <b>Главное меню</b>\n\n"
        "Выберите раздел:",
        parse_mode="HTML",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "menu_settings")
async def callback_menu_settings(callback: CallbackQuery):
    """Show settings menu"""
    user_id = callback.from_user.id
    
    # Get user profile
    async with get_db() as db:
        result = await db.execute(
            select(User).where(User.telegram_user_id == user_id)
        )
        user = result.scalar_one_or_none()
    
    if not user:
        await callback.answer("Используй /start для начала работы", show_alert=True)
        return
    
    # Format settings
    gender_ru = "Мужской" if user.gender == "male" else "Женский"
    notifications_status = "Включены ✅" if user.notifications_enabled else "Выключены ❌"
    goal_display = user.goal if user.goal else "Не указана"
    medical_display = user.medical_recommendations[:50] + "..." if user.medical_recommendations and len(user.medical_recommendations) > 50 else (user.medical_recommendations if user.medical_recommendations else "Не указаны")
    
    settings_text = (
        "⚙️ <b>Настройки</b>\n\n"
        "<b>Параметры:</b>\n"
        f"  Пол: {gender_ru}\n"
        f"  Возраст: {user.age} лет\n"
        f"  Рост: {user.height} см\n\n"
        "<b>🎯 Твоя цель:</b>\n"
        f"  {goal_display}\n\n"
        "<b>🏥 Врачебные рекомендации:</b>\n"
        f"  {medical_display}\n\n"
        "<b>🔔 Уведомления:</b>\n"
        f"  {notifications_status}\n"
        f"  🍳 Завтрак: {user.breakfast_time}\n"
        f"  🍽 Обед: {user.lunch_time}\n"
        f"  🍴 Ужин: {user.dinner_time}\n"
        f"  🌙 Напоминание: {user.evening_reminder_time}\n"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Настройка профиля", callback_data="menu_profile_settings")],
        [InlineKeyboardButton(text="🎯 Установить цель", callback_data="set_goal")],
        [InlineKeyboardButton(text="🏥 Врачебные рекомендации", callback_data="set_medical")],
        [InlineKeyboardButton(text="🍳 Рекомендации по питанию", callback_data="detailed_nutrition")],
        [InlineKeyboardButton(text="💪 Рекомендации по тренировкам", callback_data="detailed_workout")],
        [InlineKeyboardButton(text="🔔 Вкл/выкл уведомления", callback_data="toggle_notifications")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main_menu")],
    ])
    
    await callback.message.edit_text(settings_text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "menu_profile_settings")
async def callback_menu_profile_settings(callback: CallbackQuery):
    """Show profile settings submenu"""
    user_id = callback.from_user.id
    
    # Get user profile
    async with get_db() as db:
        result = await db.execute(
            select(User).where(User.telegram_user_id == user_id)
        )
        user = result.scalar_one_or_none()
    
    if not user:
        await callback.answer("Используй /start для начала работы", show_alert=True)
        return
    
    goal_display = user.goal if user.goal else "Не указана"
    medical_display = user.medical_recommendations if user.medical_recommendations else "Не указаны"
    
    settings_text = (
        "👤 <b>Настройка профиля</b>\n\n"
        "<b>Текущие параметры:</b>\n"
        f"  Возраст: {user.age} лет\n"
        f"  Рост: {user.height} см\n\n"
        "<b>🎯 Твоя цель:</b>\n"
        f"  {goal_display}\n\n"
        "<b>🏥 Врачебные рекомендации:</b>\n"
        f"  {medical_display}\n\n"
        "<b>Коэффициенты расчёта:</b>\n"
        f"  Ккал на шаг: {user.step_kcal_coef}\n"
        f"  Зал (ккал/час): {user.gym_kcal_per_hour}\n"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Изменить цель", callback_data="set_goal")],
        [InlineKeyboardButton(text="🏥 Изменить врачебные рекомендации", callback_data="set_medical")],
        [InlineKeyboardButton(text="✏️ Изменить возраст", callback_data="edit_age")],
        [InlineKeyboardButton(text="✏️ Изменить рост", callback_data="edit_height")],
        [InlineKeyboardButton(text="✏️ Изменить ккал/шаг", callback_data="edit_step_coef")],
        [InlineKeyboardButton(text="✏️ Изменить ккал зал", callback_data="edit_gym_kcal")],
        [InlineKeyboardButton(text="⏰ Настроить время уведомлений", callback_data="setup_notifications")],
        [InlineKeyboardButton(text="◀️ Назад к настройкам", callback_data="menu_settings")],
    ])
    
    await callback.message.edit_text(settings_text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "menu_stats")
async def callback_menu_stats(callback: CallbackQuery):
    """Show statistics menu"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Сегодня", callback_data="stats_today")],
        [InlineKeyboardButton(text="📆 Вчера", callback_data="stats_yesterday")],
        [InlineKeyboardButton(text="📊 Неделя", callback_data="stats_week")],
        [InlineKeyboardButton(text="📥 Экспорт в Excel", callback_data="stats_export")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main_menu")],
    ])
    
    await callback.message.edit_text(
        "📊 <b>Сводка и статистика</b>\n\n"
        "Выберите период:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "menu_nutrition")
async def callback_menu_nutrition(callback: CallbackQuery):
    """Show nutrition recommendations menu"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍳 Завтрак", callback_data="meal_breakfast")],
        [InlineKeyboardButton(text="🍽 Обед", callback_data="meal_lunch")],
        [InlineKeyboardButton(text="🍴 Ужин", callback_data="meal_dinner")],
        [InlineKeyboardButton(text="🥤 Перекус", callback_data="meal_snack")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main_menu")],
    ])
    
    await callback.message.edit_text(
        "🍽 <b>Рекомендации питания</b>\n\n"
        "Выберите прием пищи, чтобы получить персонализированные рекомендации с рецептами:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "menu_add")
async def callback_menu_add(callback: CallbackQuery):
    """Show add entry info"""
    await callback.message.edit_text(
        "📝 <b>Добавить запись</b>\n\n"
        "Для добавления записи используйте:\n\n"
        "• <code>/add</code> - ввести данные за день\n"
        "• <code>/mode</code> - изменить режим ввода\n"
        "• Отправьте фото еды для автоматического распознавания\n\n"
        "Или просто начните вводить данные в свободной форме!",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main_menu")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_main_menu")
async def callback_back_to_main_menu(callback: CallbackQuery):
    """Return to main menu"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu_settings")],
        [InlineKeyboardButton(text="📊 Сводка и статистика", callback_data="menu_stats")],
        [InlineKeyboardButton(text="🍽 Рекомендации питания", callback_data="menu_nutrition")],
        [InlineKeyboardButton(text="📝 Добавить запись", callback_data="menu_add")],
    ])
    
    await callback.message.edit_text(
        "🏠 <b>Главное меню</b>\n\n"
        "Выберите раздел:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()
