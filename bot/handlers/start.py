"""
Start handler - /start command
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from bot.config import settings
from bot.database import get_db, User, InputMode
from bot.ai.recommendations_provider import RecommendationsProvider
from bot.keyboards import get_main_keyboard

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command"""
    user_id = message.from_user.id
    
    # Get or create user in database
    async with get_db() as db:
        result = await db.execute(
            select(User).where(User.telegram_user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            # Create new user
            is_owner = (user_id == settings.OWNER_TELEGRAM_ID)
            user = User(
                telegram_user_id=user_id,
                gender="male",
                age=28,
                height=179,
                input_mode=InputMode.GUIDED,
                timezone=settings.TIMEZONE,
                is_owner=is_owner,
                is_allowed=is_owner,  # Owner is always allowed, others need approval
                profile_completed=False  # New users need to complete onboarding
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            
            # Start onboarding for new users (both owner and regular)
            if is_owner:
                await message.answer(
                    "👑 <b>Добро пожаловать, владелец!</b>\n\n"
                    "У вас полный доступ к боту.\n\n"
                    "<b>Команды владельца:</b>\n"
                    "/allow <user_id> - разрешить доступ\n"
                    "/disallow <user_id> - запретить доступ\n"
                    "/users - список пользователей",
                    parse_mode="HTML"
                )
            else:
                await message.answer(
                    f"👋 <b>Привет, {message.from_user.first_name}!</b>\n\n"
                    "📝 Вы зарегистрированы в боте.\n\n"
                    "⏳ <b>Ожидайте одобрения владельца</b>\n\n"
                    f"Ваш ID: <code>{user_id}</code>\n"
                    "Отправьте этот ID владельцу бота для получения доступа.",
                    parse_mode="HTML"
                )
            
            # Start onboarding process
            from bot.handlers.onboarding import start_onboarding
            await start_onboarding(message, state, user)
            return
        
        # Check access for existing users
        if not user.is_allowed and not user.is_owner:
            await message.answer(
                f"🔒 <b>Доступ не разрешён</b>\n\n"
                f"Ваш ID: <code>{user_id}</code>\n"
                "Отправьте этот ID владельцу бота для получения доступа.\n\n"
                "Или свяжитесь с владельцем."
            )
            return
            
            welcome_text = (
                "👋 Добро пожаловать в бот «Дневник питания и расхода»!\n\n"
                "Я помогу тебе отслеживать:\n"
                "• Питание и калории\n"
                "• Физическую активность (шаги, тренировки)\n"
                "• Сон и параметры тела\n"
                "• Баланс калорий\n\n"
                "📝 Доступные команды:\n"
                "/mode - Выбрать режим ввода (свободный/пошаговый)\n"
                "/today - Сводка за сегодня\n"
                "/yesterday - Сводка за вчера\n"
                "/week - Статистика за неделю\n"
                "/export - Экспорт в Excel\n"
                "/settings - Настройки профиля\n"
                "/help - Справка. Полный список команд\n\n"
                "Текущий режим ввода: <b>Пошаговый</b>\n"
                "Используй /mode для изменения."
            )
        else:
            welcome_text = (
                "👋 С возвращением!\n\n"
                "📝 Доступные команды:\n"
                "/mode - Выбрать режим ввода\n"
                "/today - Сводка за сегодня\n"
                "/yesterday - Сводка за вчера\n"
                "/week - Статистика за неделю\n"
                "/export - Экспорт в Excel\n"
                "/settings - Настройки профиля\n"
                "/help - Справка. Полный список команд\n\n"
                f"Текущий режим ввода: <b>{'Свободный' if user.input_mode == InputMode.FREE else 'Пошаговый'}</b>"
            )
    
    await message.answer(welcome_text, parse_mode="HTML", reply_markup=get_main_keyboard())


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command"""
    user_id = message.from_user.id
    
    # Check if user exists
    async with get_db() as db:
        result = await db.execute(
            select(User).where(User.telegram_user_id == user_id)
        )
        user = result.scalar_one_or_none()
    
    if user and user.is_owner:
        help_text = (
            "📚 <b>Справка по использованию бота (Владелец)</b>\n\n"
            "<b>👑 Команды владельца:</b>\n"
            "/allow [user_id] - разрешить доступ пользователю\n"
            "/disallow [user_id] - запретить доступ\n"
            "/users - список всех пользователей\n\n"
            "<b>🏠 Главное меню:</b>\n"
            "/menu - Открыть главное меню с разделами\n\n"
            "<b>📝 Основные команды:</b>\n"
            "/mode - Выбрать режим ввода (свободный/пошаговый)\n"
            "/add - Добавить данные за день (пошаговый режим)\n"
            "/today - Сводка за сегодня\n"
            "/yesterday - Сводка за вчера\n"
            "/week - Статистика за неделю\n"
            "/export - Экспорт в Excel\n"
            "/settings - Настройки профиля\n\n"
            "<b>🍽 Рекомендации питания:</b>\n"
            "/breakfast - Варианты завтрака\n"
            "/lunch - Варианты обеда\n"
            "/dinner - Варианты ужина\n"
            "/snack - Варианты перекуса\n\n"
            "<b>💡 Совет:</b> Используй /menu для удобной навигации!\n\n"
            "<b>Режимы ввода:</b>\n"
            "• <b>Свободный</b> - пишешь всё одним сообщением\n"
            "  Пример: \"Сон: 22:30-07:00, Шаги: 6200, Зал 60 мин, Ккал: 1850\"\n"
            "• <b>Пошаговый</b> - бот задаёт вопросы по порядку (/add)\n\n"
            "<b>📸 Фото распознавание:</b>\n"
            "Просто отправь фото еды - бот распознает и посчитает калории!\n\n"
            "<b>🤖 AI помощь:</b>\n"
            "• Текст без калорий - Ollama оценит\n"
            "• Фото еды - Gemini Vision проанализирует"
        )
    else:
        help_text = (
            "📚 <b>Справка по использованию бота</b>\n\n"
            "<b>🏠 Главное меню:</b>\n"
            "/menu - Открыть главное меню с разделами\n\n"
            "<b>📝 Основные команды:</b>\n"
            "/mode - Выбрать режим ввода (свободный/пошаговый)\n"
            "/add - Добавить данные за день (пошаговый режим)\n"
            "/today - Сводка за сегодня\n"
            "/yesterday - Сводка за вчера\n"
            "/week - Статистика за неделю\n"
            "/export - Экспорт в Excel\n"
            "/settings - Настройки профиля\n\n"
            "<b>🍽 Рекомендации питания:</b>\n"
            "/breakfast - Варианты завтрака\n"
            "/lunch - Варианты обеда\n"
            "/dinner - Варианты ужина\n"
            "/snack - Варианты перекуса\n\n"
            "<b>💡 Совет:</b> Используй /menu для удобной навигации!\n\n"
            "<b>Режимы ввода:</b>\n"
            "• <b>Свободный</b> - пишешь всё одним сообщением\n"
            "  Пример: \"Сон: 22:30-07:00, Шаги: 6200, Зал 60 мин, Ккал: 1850\"\n"
            "• <b>Пошаговый</b> - бот задаёт вопросы по порядку (/add)\n\n"
            "<b>📸 Фото распознавание:</b>\n"
            "Просто отправь фото еды - бот распознает и посчитает калории!"
        )
    
    await message.answer(help_text, parse_mode="HTML")


@router.callback_query(F.data == "open_settings")
async def callback_open_settings(callback: CallbackQuery):
    """Open settings menu"""
    from bot.handlers.settings import cmd_settings
    await cmd_settings(callback.message)
    await callback.answer()


@router.callback_query(F.data == "detailed_nutrition")
async def callback_detailed_nutrition(callback: CallbackQuery):
    """Show detailed nutrition recommendation"""
    await callback.answer()
    user_id = callback.from_user.id
    
    async with get_db() as db:
        result = await db.execute(
            select(User).where(User.telegram_user_id == user_id)
        )
        user = result.scalar_one_or_none()
    
    if not user:
        return
    
    await callback.message.answer("⏳ Генерирую подробные рекомендации по питанию...")
    
    try:
        provider = RecommendationsProvider()
        nutrition_rec = await provider.generate_detailed_nutrition_recommendation(user)
        await callback.message.answer(nutrition_rec, parse_mode="HTML")
    except Exception as e:
        await callback.message.answer("❌ Не удалось сгенерировать рекомендации. Попробуйте позже.")


@router.callback_query(F.data == "detailed_workout")
async def callback_detailed_workout(callback: CallbackQuery):
    """Show detailed workout recommendation"""
    await callback.answer()
    user_id = callback.from_user.id
    
    async with get_db() as db:
        result = await db.execute(
            select(User).where(User.telegram_user_id == user_id)
        )
        user = result.scalar_one_or_none()
    
    if not user:
        return
    
    await callback.message.answer("⏳ Генерирую подробные рекомендации по тренировкам...")
    
    try:
        provider = RecommendationsProvider()
        workout_rec = await provider.generate_detailed_workout_recommendation(user)
        await callback.message.answer(workout_rec, parse_mode="HTML")
    except Exception as e:
        await callback.message.answer("❌ Не удалось сгенерировать рекомендации. Попробуйте позже.")
