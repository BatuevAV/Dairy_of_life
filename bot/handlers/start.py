"""
Start handler - /start command
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from bot.config import settings
from bot.database import get_db, User, InputMode

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
                is_allowed=is_owner  # Owner is always allowed, others need approval
            )
            db.add(user)
            await db.commit()
            
            # Welcome message for new users
            if is_owner:
                await message.answer(
                    "👑 <b>Добро пожаловать, владелец!</b>\n\n"
                    "У вас полный доступ к боту.\n\n"
                    "<b>Управление пользователями:</b>\n"
                    "/allow <user_id> - разрешить доступ\n"
                    "/disallow <user_id> - запретить доступ\n"
                    "/users - список пользователей\n\n"
                    "Сначала настройте профиль: /settings"
                )
            else:
                await message.answer(
                    f"👋 <b>Привет, {message.from_user.first_name}!</b>\n\n"
                    "📝 Вы зарегистрированы в боте.\n\n"
                    "⏳ <b>Ожидайте одобрения владельца</b>\n\n"
                    f"Ваш ID: <code>{user_id}</code>\n"
                    "Отправьте этот ID владельцу бота для получения доступа."
                )
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
                "/help - Справка\n\n"
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
                "/help - Справка\n\n"
                f"Текущий режим ввода: <b>{'Свободный' if user.input_mode == InputMode.FREE else 'Пошаговый'}</b>"
            )
    
    await message.answer(welcome_text, parse_mode="HTML")


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
            "/allow <user_id> - разрешить доступ пользователю\n"
            "/disallow <user_id> - запретить доступ\n"
            "/users - список всех пользователей\n\n"
            "<b>📝 Основные команды:</b>\n"
            "/mode - Выбрать режим ввода (свободный/пошаговый)\n"
            "/today - Сводка за сегодня\n"
            "/yesterday - Сводка за вчера\n"
            "/week - Статистика за неделю\n"
            "/export - Экспорт в Excel\n"
            "/settings - Настройки профиля\n\n"
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
            "<b>📝 Основные команды:</b>\n"
            "/mode - Выбрать режим ввода (свободный/пошаговый)\n"
            "/today - Сводка за сегодня\n"
            "/yesterday - Сводка за вчера\n"
            "/week - Статистика за неделю\n"
            "/export - Экспорт в Excel\n"
            "/settings - Настройки профиля\n\n"
            "<b>Режимы ввода:</b>\n"
            "• <b>Свободный</b> - пишешь всё одним сообщением\n"
            "  Пример: \"Сон: 22:30-07:00, Шаги: 6200, Зал 60 мин, Ккал: 1850\"\n"
            "• <b>Пошаговый</b> - бот задаёт вопросы по порядку (/add)\n\n"
            "<b>📸 Фото распознавание:</b>\n"
            "Просто отправь фото еды - бот распознает и посчитает калории!"
        )
    
    await message.answer(help_text, parse_mode="HTML")
