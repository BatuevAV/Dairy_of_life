"""Check if MealEntry records exist"""
import asyncio
from sqlalchemy import select, text
from bot.database.db import async_session_maker

async def check_meals():
    async with async_session_maker() as session:
        result = await session.execute(
            text('SELECT COUNT(*) FROM meal_entries WHERE entry_date = CURRENT_DATE')
        )
        count = result.scalar()
        print(f'✅ MealEntry records for today: {count}')
        
        if count > 0:
            result = await session.execute(
                text('SELECT meal_type, meal_time, kcal, food_description FROM meal_entries WHERE entry_date = CURRENT_DATE LIMIT 5')
            )
            meals = result.fetchall()
            print('\nMeals:')
            for meal in meals:
                print(f'  Type: {meal[0]}, Time: {meal[1]}, Kcal: {meal[2]}')
                print(f'  Food: {meal[3][:50] if meal[3] else "None"}')
        else:
            print('❌ No meals found for today!')
            print('Try adding food again with meal type selection.')

asyncio.run(check_meals())
