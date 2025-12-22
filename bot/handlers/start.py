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
    
    # Check if user is owner
    if user_id != settings.OWNER_TELEGRAM_ID:
        await message.answer(
            "❌ Доступ запрещён.\n"
            "Этот бот доступен только владельцу."
        )
        return
    
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
                is_allowed=is_owner  # Owner is always allowed
            )
            db.add(user)
            await db.commit()
            
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
    help_text = (
        "📚 <b>Справка по использованию бота</b>\n\n"
        "<b>Режимы ввода:</b>\n"
        "• <b>Свободный</b> - пишешь всё одним сообщением\n"
        "  Пример: \"Сон: 22:30-07:00, Шаги: 6200, Зал 60 мин, Ккал: 1850\"\n\n"
        "• <b>Пошаговый</b> - бот задаёт вопросы по порядку\n\n"
        "<b>Команды:</b>\n"
        "/start - Начать работу с ботом\n"
        "/mode - Выбрать режим ввода\n"
        "/today - Сводка за сегодня\n"
        "/yesterday - Сводка за вчера\n"
        "/week - Статистика за 7 дней\n"
        "/export - Экспорт данных в Excel\n"
        "/settings - Настройки профиля и расчётов\n"
        "/help - Эта справка\n\n"
        "<b>Формат свободного ввода:</b>\n"
        "Сон: 22:30-07:00 (или просто \"7 ч\")\n"
        "Шаги: 6200\n"
        "Тренировка: зал 60 мин (или \"плавание 45 мин\")\n"
        "Еда: [описание] или Ккал: 1850\n"
        "БЖУ: 150/60/180 (необязательно)\n"
        "Вес: 75.5 кг\n"
        "Талия: 85 см\n\n"
        "Бот автоматически считает BMR, расход калорий и баланс."
    )
    
    await message.answer(help_text, parse_mode="HTML")
