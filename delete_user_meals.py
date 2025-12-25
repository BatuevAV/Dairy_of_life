"""
Delete all data entries for a specific user (keep profile)
"""
import asyncio
from sqlalchemy import delete
from bot.database import get_db
from bot.database.models import MealEntry, DayEntry


async def delete_user_data(user_id: int):
    """Delete all data entries for a user but keep the profile"""
    async with get_db() as db:
        # Delete meal entries
        meal_result = await db.execute(
            delete(MealEntry).where(MealEntry.user_id == user_id)
        )
        meals_deleted = meal_result.rowcount
        
        # Delete day entries
        day_result = await db.execute(
            delete(DayEntry).where(DayEntry.user_id == user_id)
        )
        days_deleted = day_result.rowcount
        
        await db.commit()
        
        print(f"✅ Удалено записей о еде: {meals_deleted}")
        print(f"✅ Удалено дневных записей: {days_deleted}")
        print(f"📋 Профиль пользователя сохранен")


if __name__ == "__main__":
    user_id = 1  # User ID to delete data for
    print(f"Удаление всех данных для пользователя с ID {user_id} (профиль сохраняется)...")
    asyncio.run(delete_user_data(user_id))
    print("Готово!")
