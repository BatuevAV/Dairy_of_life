"""
Migration: Add profile_completed column to users table
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from bot.database import get_db


async def migrate():
    """Add profile_completed column"""
    async with get_db() as db:
        # Check if column exists
        result = await db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='profile_completed'
        """))
        
        if result.fetchone():
            print("✅ Column profile_completed already exists")
            return
        
        # Add column
        await db.execute(text("""
            ALTER TABLE users 
            ADD COLUMN profile_completed BOOLEAN DEFAULT FALSE
        """))
        await db.commit()
        print("✅ Added profile_completed column")


if __name__ == "__main__":
    asyncio.run(migrate())
