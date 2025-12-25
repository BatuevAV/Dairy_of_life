"""
Check if is_owner column exists
"""
import asyncio
from bot.database.db import async_session_maker
from sqlalchemy import text

async def check_column():
    async with async_session_maker() as session:
        result = await session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' 
            ORDER BY ordinal_position
        """))
        columns = [row[0] for row in result]
        print("Existing columns in users table:")
        for col in columns:
            print(f"  - {col}")
        
        if 'is_owner' in columns:
            print("\n✅ is_owner column exists")
        else:
            print("\n❌ is_owner column does NOT exist")
            print("\nTrying to add it...")
            await session.execute(text("ALTER TABLE users ADD COLUMN is_owner BOOLEAN DEFAULT FALSE"))
            await session.commit()
            print("✅ is_owner column added successfully")

if __name__ == "__main__":
    asyncio.run(check_column())
