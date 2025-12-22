"""
Migration script - добавление полей для фото-распознавания
"""
import asyncio
from sqlalchemy import text
from bot.database.db import get_db, engine


async def apply_photo_migrations():
    """Добавить колонки для фото-распознавания"""
    
    migrations = [
        # User table: photo settings
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS save_photos BOOLEAN DEFAULT FALSE;
        """,
        
        # DayEntry table: photo metadata
        """
        ALTER TABLE day_entries
        ADD COLUMN IF NOT EXISTS photo_analyzed BOOLEAN DEFAULT FALSE;
        """,
        """
        ALTER TABLE day_entries
        ADD COLUMN IF NOT EXISTS photo_file_id VARCHAR(200);
        """,
        """
        ALTER TABLE day_entries
        ADD COLUMN IF NOT EXISTS photo_description TEXT;
        """,
        """
        ALTER TABLE day_entries
        ADD COLUMN IF NOT EXISTS photo_clarifications_json TEXT;
        """,
        """
        ALTER TABLE day_entries
        ADD COLUMN IF NOT EXISTS food_description TEXT;
        """,
    ]
    
    async with get_db() as session:
        try:
            for i, migration in enumerate(migrations, 1):
                print(f"[{i}/{len(migrations)}] Выполняю миграцию...")
                await session.execute(text(migration))
            
            await session.commit()
            print("\n✅ Все миграции фото-функций применены успешно!")
            print("\nДобавлены колонки:")
            print("  users:")
            print("    - save_photos (настройка сохранения фото)")
            print("  day_entries:")
            print("    - photo_analyzed (было ли фото)")
            print("    - photo_file_id (Telegram file_id)")
            print("    - photo_description (что видит AI)")
            print("    - photo_clarifications_json (вопросы/ответы)")
            print("    - food_description (описание еды)")
            
        except Exception as e:
            print(f"\n❌ Ошибка при применении миграций: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    print("🔄 Начинаю миграции для фото-распознавания...\n")
    asyncio.run(apply_photo_migrations())
