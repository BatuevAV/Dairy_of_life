"""
Mode selection handler
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, update

from bot.config import settings
from bot.database import get_db, User, InputMode
from bot.utils import check_user_access

router = Router()


@router.message(Command("mode"))
async def cmd_mode(message: Message):
    """Handle /mode command"""
    user_id = message.from_user.id
    
    # Check access
    user, has_access, error_msg = await check_user_access(user_id)
    if not has_access:
        await message.answer(error_msg)
        return
    
    # Get current mode
    current_mode = "Свободный" if user.input_mode == InputMode.FREE else "Пошаговый"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✍️ Свободный", callback_data="mode_free"),
            InlineKeyboardButton(text="📋 Пошаговый", callback_data="mode_guided")
        ]
    ])
    
    await message.answer(
        f"<b>Выбери режим ввода:</b>\n\n"
        f"<b>✍️ Свободный режим</b> - пишешь всю информацию одним сообщением. "
        f"Бот распознает данные и попросит подтверждение.\n\n"
        f"<b>📋 Пошаговый режим</b> - бот задаёт вопросы по порядку. "
        f"Надёжнее для точного ввода.\n\n"
        f"Текущий режим: <b>{current_mode}</b>",
        parse_mode="HTML",
        reply_markup=keyboard
    )


@router.callback_query(F.data.startswith("mode_"))
async def callback_mode(callback: CallbackQuery):
    """Handle mode selection callback"""
    user_id = callback.from_user.id
    
    # Check access
    user, has_access, error_msg = await check_user_access(user_id)
    if not has_access:
        await callback.answer("Доступ запрещён")
        return
    
    mode_str = callback.data.split("_")[1]  # free or guided
    new_mode = InputMode.FREE if mode_str == "free" else InputMode.GUIDED
    
    # Update mode in database
    async with get_db() as db:
        await db.execute(
            update(User)
            .where(User.telegram_user_id == user_id)
            .values(input_mode=new_mode)
        )
        await db.commit()
    
    mode_name = "Свободный" if new_mode == InputMode.FREE else "Пошаговый"
    
    await callback.message.edit_text(
        f"✅ Режим изменён на: <b>{mode_name}</b>\n\n"
        f"{'Теперь можешь писать всю информацию одним сообщением.' if new_mode == InputMode.FREE else 'Теперь бот будет задавать вопросы по порядку.'}",
        parse_mode="HTML"
    )
    
    await callback.answer()
