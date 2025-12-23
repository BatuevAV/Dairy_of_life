"""
Migration to add goal and medical_recommendations fields to users table
"""
import asyncio
from sqlalchemy import text
from bot.database.db import async_session_maker

async def apply_migration():
    """Add goal and medical_recommendations columns"""
    print("🔄 Starting migration: add goal and medical_recommendations fields...")
    
    async with async_session_maker() as session:
        try:
            # Add goal column
            print("Adding goal column...")
            await session.execute(text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS goal TEXT
            """))
            
            # Add medical_recommendations column
            print("Adding medical_recommendations column...")
            await session.execute(text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS medical_recommendations TEXT
            """))
            
            await session.commit()
            print("✅ Migration completed successfully!")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Migration failed: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(apply_migration())
