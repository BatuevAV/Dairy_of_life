"""
Применение миграций БД без проверок
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from bot.database.db import engine
from sqlalchemy import text


async def apply_migrations():
    """Применить миграции к БД"""
    
    print("🚀 Применяю миграции БД для AI-функционала...\n")
    
    async with engine.begin() as conn:
        # 1. Добавление полей мультиюзера в таблицу users
        print("📝 Добавляю колонки в таблицу users...")
        await conn.execute(text("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS is_owner BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS is_allowed BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS allowed_by BIGINT,
            ADD COLUMN IF NOT EXISTS ai_requests_today INTEGER DEFAULT 0,
            ADD COLUMN IF NOT EXISTS ai_requests_limit INTEGER DEFAULT 30,
            ADD COLUMN IF NOT EXISTS last_ai_request TIMESTAMP WITHOUT TIME ZONE;
        """))
        print("✅ Колонки users добавлены\n")
        
        # 2. Добавление полей AI-оценки в таблицу day_entries
        print("📝 Добавляю колонки в таблицу day_entries...")
        await conn.execute(text("""
            ALTER TABLE day_entries
            ADD COLUMN IF NOT EXISTS food_ai_estimated BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS food_ai_model VARCHAR(50),
            ADD COLUMN IF NOT EXISTS food_ai_confidence FLOAT,
            ADD COLUMN IF NOT EXISTS food_items_json TEXT;
        """))
        print("✅ Колонки day_entries добавлены\n")
        
        # 3. Установка текущего пользователя как owner
        print("📝 Устанавливаю владельца бота...")
        result = await conn.execute(text("""
            UPDATE users
            SET is_owner = TRUE, is_allowed = TRUE
            WHERE telegram_user_id = 997743143;
        """))
        print(f"✅ Обновлено записей: {result.rowcount}\n")
        
        print("🎉 Все миграции успешно применены!\n")
        print("✅ Теперь можно запустить бота: python -m bot.main")


if __name__ == "__main__":
    asyncio.run(apply_migrations())
