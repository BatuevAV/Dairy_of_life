"""
Keyboard layouts for the bot
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Get main reply keyboard with menu button"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Меню")]
        ],
        resize_keyboard=True,
        persistent=True  # Keyboard stays visible
    )
    return keyboard
