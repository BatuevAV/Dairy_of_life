"""
Admin handler - owner commands for managing access
"""
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select, update

from bot.config import settings
from bot.database import get_db, User

router = Router()


@router.message(Command("allow"))
async def cmd_allow(message: Message):
    """Allow a user to access the bot (owner only)"""
    user_id = message.from_user.id
    
    # Check if user is owner
    async with get_db() as db:
        result = await db.execute(
            select(User).where(User.telegram_user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.is_owner:
            await message.answer("❌ Эта команда доступна только владельцу бота")
            return
    
    # Parse user ID from command
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "📝 Использование:\n"
            "/allow <telegram_user_id>\n\n"
            "Пример: /allow 123456789\n\n"
            "Или перешли сообщение пользователя и используй /allow"
        )
        return
    
    try:
        target_user_id = int(args[1])
    except ValueError:
        await message.answer("❌ Неверный формат ID. Используй числовой Telegram ID.")
        return
    
    # Update or create user
    async with get_db() as db:
        result = await db.execute(
            select(User).where(User.telegram_user_id == target_user_id)
        )
        target_user = result.scalar_one_or_none()
        
        if target_user:
            # Update existing user
            target_user.is_allowed = True
            target_user.allowed_by = user_id
            await db.commit()
            await message.answer(
                f"✅ Пользователь {target_user_id} получил доступ к боту"
            )
        else:
            # Create new allowed user
            new_user = User(
                telegram_user_id=target_user_id,
                is_allowed=True,
                is_owner=False,
                allowed_by=user_id
            )
            db.add(new_user)
            await db.commit()
            await message.answer(
                f"✅ Пользователь {target_user_id} добавлен и получил доступ к боту"
            )


@router.message(Command("disallow"))
async def cmd_disallow(message: Message):
    """Revoke user access (owner only)"""
    user_id = message.from_user.id
    
    # Check if user is owner
    async with get_db() as db:
        result = await db.execute(
            select(User).where(User.telegram_user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.is_owner:
            await message.answer("❌ Эта команда доступна только владельцу бота")
            return
    
    # Parse user ID
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "📝 Использование:\n"
            "/disallow <telegram_user_id>"
        )
        return
    
    try:
        target_user_id = int(args[1])
    except ValueError:
        await message.answer("❌ Неверный формат ID")
        return
    
    # Disallow user
    async with get_db() as db:
        result = await db.execute(
            update(User)
            .where(User.telegram_user_id == target_user_id)
            .values(is_allowed=False)
        )
        await db.commit()
        
        if result.rowcount > 0:
            await message.answer(f"✅ Доступ для пользователя {target_user_id} отозван")
        else:
            await message.answer(f"❌ Пользователь {target_user_id} не найден")


@router.message(Command("users"))
async def cmd_users(message: Message):
    """List all allowed users (owner only)"""
    user_id = message.from_user.id
    
    # Check if user is owner
    async with get_db() as db:
        result = await db.execute(
            select(User).where(User.telegram_user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.is_owner:
            await message.answer("❌ Эта команда доступна только владельцу бота")
            return
        
        # Get all users
        result = await db.execute(
            select(User).order_by(User.created_at.desc())
        )
        users = result.scalars().all()
    
    if not users:
        await message.answer("📝 Нет зарегистрированных пользователей")
        return
    
    # Format user list
    text = "👥 <b>Зарегистрированные пользователи:</b>\n\n"
    
    for u in users:
        status = "👑 Владелец" if u.is_owner else ("✅ Разрешён" if u.is_allowed else "❌ Заблокирован")
        ai_usage = f"{u.ai_requests_today}/{u.ai_requests_limit}"
        text += f"• ID: <code>{u.telegram_user_id}</code>\n"
        text += f"  Статус: {status}\n"
        text += f"  AI запросов сегодня: {ai_usage}\n"
        text += f"  Создан: {u.created_at.strftime('%d.%m.%Y')}\n\n"
    
    await message.answer(text, parse_mode="HTML")
