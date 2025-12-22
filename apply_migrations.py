"""
Скрипт для применения миграций БД
Добавляет новые колонки для AI-функционала и мультиюзера
"""
import asyncio
import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from bot.database.db import engine
from sqlalchemy import text


async def apply_migrations():
    """Применить миграции к БД"""
    
    migrations = [
        # 1. Добавление полей мультиюзера в таблицу users
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS is_owner BOOLEAN DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS is_allowed BOOLEAN DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS allowed_by BIGINT,
        ADD COLUMN IF NOT EXISTS ai_requests_today INTEGER DEFAULT 0,
        ADD COLUMN IF NOT EXISTS ai_requests_limit INTEGER DEFAULT 30,
        ADD COLUMN IF NOT EXISTS last_ai_request TIMESTAMP WITHOUT TIME ZONE;
        """,
        
        # 2. Добавление полей AI-оценки в таблицу day_entries
        """
        ALTER TABLE day_entries
        ADD COLUMN IF NOT EXISTS food_ai_estimated BOOLEAN DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS food_ai_model VARCHAR(50),
        ADD COLUMN IF NOT EXISTS food_ai_confidence FLOAT,
        ADD COLUMN IF NOT EXISTS food_items_json TEXT;
        """,
        
        # 3. Установка текущего пользователя как owner
        """
        UPDATE users
        SET is_owner = TRUE, is_allowed = TRUE
        WHERE telegram_user_id = 997743143;
        """
    ]
    
    async with engine.begin() as conn:
        for i, migration in enumerate(migrations, 1):
            print(f"\n🔄 Применяю миграцию {i}/{len(migrations)}...")
            try:
                await conn.execute(text(migration))
                print(f"✅ Миграция {i} успешно применена!")
            except Exception as e:
                print(f"❌ Ошибка в миграции {i}: {e}")
                raise
        
        # Проверка изменений
        print("\n📊 Проверка изменений в таблице users:")
        result = await conn.execute(text("""
            SELECT 
                telegram_user_id,
                username,
                is_owner,
                is_allowed,
                ai_requests_today,
                ai_requests_limit
            FROM users
            LIMIT 5;
        """))
        
        rows = result.fetchall()
        if rows:
            print("\n👥 Пользователи в БД:")
            for row in rows:
                print(f"  • ID: {row[0]}, Username: {row[1]}, Owner: {row[2]}, Allowed: {row[3]}, AI requests: {row[4]}/{row[5]}")
        else:
            print("  (нет пользователей в БД)")
        
        print("\n📊 Проверка изменений в таблице day_entries:")
        result = await conn.execute(text("""
            SELECT COUNT(*) as total,
                   COUNT(food_ai_estimated) as has_ai_field
            FROM day_entries;
        """))
        
        row = result.fetchone()
        print(f"  • Всего записей: {row[0]}")
        print(f"  • Поле food_ai_estimated добавлено: {'✅' if row[1] is not None else '❌'}")
    
    print("\n✅ Все миграции успешно применены!")
    print("\n📝 Следующие шаги:")
    print("  1. Перезапустите бота: source venv/bin/activate && python -m bot.main")
    print("  2. Отправьте боту текст с едой без калорий")
    print("  3. Проверьте, что AI оценивает калорийность")


if __name__ == "__main__":
    print("🚀 Применение миграций БД для AI-функционала...")
    asyncio.run(apply_migrations())
