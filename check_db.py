"""
Проверка колонок в таблице users
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from bot.database.db import engine
from sqlalchemy import text


async def check_columns():
    """Проверить наличие колонок в таблице users"""
    
    async with engine.begin() as conn:
        # Получаем все колонки таблицы users
        result = await conn.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'users'
            ORDER BY ordinal_position;
        """))
        
        columns = result.fetchall()
        
        print("\n📊 Колонки таблицы users:\n")
        print(f"{'Колонка':<30} {'Тип':<20} {'NULL?':<10}")
        print("=" * 60)
        
        required_columns = ['is_owner', 'is_allowed', 'allowed_by', 'ai_requests_today', 'ai_requests_limit', 'last_ai_request']
        found_columns = []
        
        for col in columns:
            col_name = col[0]
            col_type = col[1]
            nullable = col[2]
            print(f"{col_name:<30} {col_type:<20} {nullable:<10}")
            
            if col_name in required_columns:
                found_columns.append(col_name)
        
        print("\n" + "=" * 60)
        print("\n✅ Найденные AI колонки:")
        for col in required_columns:
            if col in found_columns:
                print(f"  ✅ {col}")
            else:
                print(f"  ❌ {col} - ОТСУТСТВУЕТ!")
        
        # Проверяем day_entries
        result = await conn.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'day_entries'
            AND column_name LIKE '%ai%';
        """))
        
        ai_columns = result.fetchall()
        
        print("\n📊 AI колонки в day_entries:")
        for col in ai_columns:
            print(f"  ✅ {col[0]} ({col[1]})")
        
        if len(found_columns) == len(required_columns):
            print("\n🎉 Все колонки на месте! Миграции применены успешно.")
            return True
        else:
            print(f"\n❌ Отсутствуют {len(required_columns) - len(found_columns)} колонки")
            return False


if __name__ == "__main__":
    result = asyncio.run(check_columns())
    sys.exit(0 if result else 1)
