"""
Migration script: Add notifications settings and MealEntry table
"""
import asyncio
from sqlalchemy import text
from bot.database import get_db


async def migrate():
    """Apply migration"""
    async with get_db() as db:
        print("Starting migration...")
        
        # Add new columns to users table
        try:
            await db.execute(text("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS notifications_enabled BOOLEAN DEFAULT TRUE;
            """))
            print("✓ Added notifications_enabled column")
        except Exception as e:
            print(f"✗ notifications_enabled: {e}")
        
        try:
            await db.execute(text("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS breakfast_time VARCHAR(5) DEFAULT '08:00';
            """))
            print("✓ Added breakfast_time column")
        except Exception as e:
            print(f"✗ breakfast_time: {e}")
        
        try:
            await db.execute(text("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS lunch_time VARCHAR(5) DEFAULT '13:00';
            """))
            print("✓ Added lunch_time column")
        except Exception as e:
            print(f"✗ lunch_time: {e}")
        
        try:
            await db.execute(text("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS dinner_time VARCHAR(5) DEFAULT '19:00';
            """))
            print("✓ Added dinner_time column")
        except Exception as e:
            print(f"✗ dinner_time: {e}")
        
        try:
            await db.execute(text("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS evening_reminder_time VARCHAR(5) DEFAULT '21:00';
            """))
            print("✓ Added evening_reminder_time column")
        except Exception as e:
            print(f"✗ evening_reminder_time: {e}")
        
        # Create meal_entries table
        try:
            await db.execute(text("""
                CREATE TABLE IF NOT EXISTS meal_entries (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    day_entry_id INTEGER REFERENCES day_entries(id) ON DELETE SET NULL,
                    entry_date DATE NOT NULL,
                    meal_type VARCHAR(20) NOT NULL,
                    meal_time VARCHAR(5),
                    kcal FLOAT,
                    protein FLOAT,
                    fat FLOAT,
                    carbs FLOAT,
                    food_ai_estimated BOOLEAN DEFAULT FALSE,
                    food_ai_model VARCHAR(50),
                    food_ai_confidence FLOAT,
                    food_items_json TEXT,
                    photo_analyzed BOOLEAN DEFAULT FALSE,
                    photo_file_id VARCHAR(200),
                    photo_description TEXT,
                    food_description TEXT,
                    raw_text TEXT,
                    notes TEXT,
                    from_recipe BOOLEAN DEFAULT FALSE,
                    recipe_name VARCHAR(200),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            print("✓ Created meal_entries table")
        except Exception as e:
            print(f"✗ meal_entries table: {e}")
        
        # Create index on meal_entries
        try:
            await db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_meal_entries_user_date 
                ON meal_entries(user_id, entry_date);
            """))
            print("✓ Created index on meal_entries")
        except Exception as e:
            print(f"✗ index: {e}")
        
        await db.commit()
        print("\n✅ Migration completed!")


if __name__ == "__main__":
    asyncio.run(migrate())
