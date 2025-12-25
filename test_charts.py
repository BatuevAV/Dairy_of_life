"""
Script to create test data and generate Excel with charts
"""
import asyncio
from datetime import date, timedelta
from bot.database import get_db, User, DayEntry, MealEntry, WorkoutType, MealType
from bot.utils.excel_export import create_excel_export


async def create_test_data():
    """Create test data for charts"""
    async with get_db() as db:
        from sqlalchemy import select
        
        # Get user 1
        result = await db.execute(select(User).where(User.id == 1))
        user = result.scalar_one_or_none()
        
        if not user:
            print("User 1 not found")
            return None, [], []
        
        # Delete existing entries
        result = await db.execute(
            select(DayEntry).where(DayEntry.user_id == user.id)
        )
        existing = result.scalars().all()
        for entry in existing:
            await db.delete(entry)
        
        result = await db.execute(
            select(MealEntry).where(MealEntry.user_id == user.id)
        )
        existing_meals = result.scalars().all()
        for meal in existing_meals:
            await db.delete(meal)
        
        await db.commit()
        
        # Create 14 days of test data
        entries = []
        meal_entries = []
        today = date.today()
        
        for i in range(14):
            entry_date = today - timedelta(days=13 - i)
            
            # Varying data to make interesting charts
            day_of_week = entry_date.weekday()
            
            entry = DayEntry(
                user_id=user.id,
                entry_date=entry_date,
                weight=85.0 - (i * 0.3),  # Gradual weight loss
                waist=95 - i * 0.2,
                sleep_hours=7 + (i % 3),  # Vary between 7-9
                steps=8000 + (i * 200) + (day_of_week * 500),  # More steps on weekdays
                workout_type=WorkoutType.GYM if day_of_week < 5 else None,  # Gym on weekdays
                workout_minutes=60 if day_of_week < 5 else 0,
                bmr=1800,
                kcal_steps=400 + (i * 10),
                kcal_workout=300 if day_of_week < 5 else 0,
                kcal_burned_total=2500 + (i * 20),
                kcal_eaten=2200 + (i * 30) - (day_of_week * 50),  # Eat less on weekdays
                kcal_balance=(2200 + (i * 30) - (day_of_week * 50)) - (2500 + (i * 20)),
                protein=120 + (i * 2),
                fat=70 + (i * 1),
                carbs=200 + (i * 3),
            )
            
            db.add(entry)
            entries.append(entry)
            
            # Create meal entries for each day
            # Breakfast
            meal_entries.append(MealEntry(
                user_id=user.id,
                entry_date=entry_date,
                meal_type=MealType.BREAKFAST,
                meal_time="08:00",
                kcal=500 + (i * 5),
                protein=30,
                fat=15,
                carbs=60
            ))
            
            # Lunch
            meal_entries.append(MealEntry(
                user_id=user.id,
                entry_date=entry_date,
                meal_type=MealType.LUNCH,
                meal_time="13:00",
                kcal=700 + (i * 7),
                protein=40,
                fat=25,
                carbs=80
            ))
            
            # Dinner
            meal_entries.append(MealEntry(
                user_id=user.id,
                entry_date=entry_date,
                meal_type=MealType.DINNER,
                meal_time="19:00",
                kcal=600 + (i * 6),
                protein=35,
                fat=20,
                carbs=70
            ))
            
            # Snack (sometimes)
            if i % 3 == 0:
                meal_entries.append(MealEntry(
                    user_id=user.id,
                    entry_date=entry_date,
                    meal_type=MealType.SNACK,
                    meal_time="16:00",
                    kcal=200,
                    protein=10,
                    fat=8,
                    carbs=25
                ))
        
        for meal in meal_entries:
            db.add(meal)
        
        await db.commit()
        print(f"Created {len(entries)} test day entries")
        print(f"Created {len(meal_entries)} test meal entries")
        
        return user, entries, meal_entries


async def test_export():
    """Test Excel export with charts"""
    user, entries, meal_entries = await create_test_data()
    
    if not user or not entries:
        print("Failed to create test data")
        return
    
    print("\nGenerating Excel with charts...")
    try:
        buffer = create_excel_export(user, entries, meal_entries, days=14)
        
        # Save to file
        filename = "test_export_with_charts.xlsx"
        with open(filename, 'wb') as f:
            f.write(buffer.read())
        
        print(f"✅ Excel file created: {filename}")
        print("Open it to see the charts!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_export())
