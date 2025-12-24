"""
Add is_owner column to users table
"""
import asyncio
from bot.database.db import async_session_maker
from sqlalchemy import text

async def run_migration():
    async with async_session_maker() as session:
        # Add is_owner column
        await session.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_owner BOOLEAN DEFAULT FALSE"))
        await session.commit()
        print("Migration completed: is_owner column added")

if __name__ == "__main__":
    asyncio.run(run_migration())
