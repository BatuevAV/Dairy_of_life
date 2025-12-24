"""
Recreate user with correct telegram_user_id type
"""
import asyncio
from sqlalchemy import text
from bot.database.db import async_session_maker
from bot.config import settings


async def recreate_user():
    """Delete and recreate owner user"""
    owner_id = settings.OWNER_TELEGRAM_ID
    
    async with async_session_maker() as session:
        try:
            # Delete old user
            await session.execute(
                text("DELETE FROM users WHERE telegram_user_id = :user_id"),
                {"user_id": owner_id}
            )
            
            print(f"✅ Deleted old user record for {owner_id}")
            
            await session.commit()
            print("✅ Done! Now use /start in bot to recreate user")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error: {e}")
            raise


if __name__ == "__main__":
    print(f"Owner Telegram ID: {settings.OWNER_TELEGRAM_ID}")
    asyncio.run(recreate_user())
