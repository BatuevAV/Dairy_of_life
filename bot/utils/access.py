"""
Access control helpers
"""
from typing import Optional
from sqlalchemy import select
from bot.database import get_db, User


async def check_user_access(telegram_user_id: int) -> tuple[Optional[User], bool, str]:
    """
    Проверить доступ пользователя к боту
    
    Returns:
        tuple: (User object, has_access: bool, error_message: str)
    """
    async with get_db() as db:
        result = await db.execute(
            select(User).where(User.telegram_user_id == telegram_user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None, False, "❌ Сначала нажмите /start"
        
        if not user.is_allowed and not user.is_owner:
            return user, False, (
                f"🔒 <b>Доступ не разрешён</b>\n\n"
                f"Ваш ID: <code>{telegram_user_id}</code>\n"
                "Отправьте этот ID владельцу бота для получения доступа."
            )
        
        return user, True, ""


async def check_owner_access(telegram_user_id: int) -> tuple[Optional[User], bool, str]:
    """
    Проверить что пользователь - владелец
    
    Returns:
        tuple: (User object, is_owner: bool, error_message: str)
    """
    async with get_db() as db:
        result = await db.execute(
            select(User).where(User.telegram_user_id == telegram_user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None, False, "❌ Сначала нажмите /start"
        
        if not user.is_owner:
            return user, False, "❌ Эта команда доступна только владельцу бота."
        
        return user, True, ""
