"""
Migration: Change telegram_user_id from INTEGER to BIGINT
Reason: Telegram IDs can exceed int32 max value (2147483647)
"""
import asyncio
from sqlalchemy import text
from bot.database.db import async_session_maker


async def migrate():
    """Change telegram_user_id column type to BIGINT"""
    async with async_session_maker() as session:
        try:
            # PostgreSQL: ALTER COLUMN type
            await session.execute(text(
                "ALTER TABLE users ALTER COLUMN telegram_user_id TYPE BIGINT"
            ))
            
            await session.commit()
            print("✅ Successfully changed telegram_user_id to BIGINT")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Migration failed: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(migrate())
