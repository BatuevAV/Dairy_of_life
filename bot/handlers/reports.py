"""
Reports handler - /today, /yesterday, /week
"""
from datetime import date, timedelta
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select
from sqlalchemy.sql import and_

from bot.config import settings
from bot.database import get_db, User, DayEntry, MealEntry, MealType
from bot.utils import format_sleep_time, format_calories, check_user_access
from bot.handlers.export import cmd_export

router = Router()


@router.message(Command("today"))
async def cmd_today(message: Message, user_id: int = None):
    """Show today's summary"""
    if user_id is None:
        user_id = message.from_user.id
    
    # Check access
    user, has_access, error_msg = await check_user_access(user_id)
    if not has_access:
        await message.answer(error_msg)
        return
    
    today = date.today()
    
    async with get_db() as db:
        # Get user
        result = await db.execute(
            select(User).where(User.telegram_user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer("Используй /start для начала работы")
            return
        
        # Get today's entry
        result = await db.execute(
            select(DayEntry).where(
                and_(
                    DayEntry.user_id == user.id,
                    DayEntry.entry_date == today
                )
            )
        )
        entry = result.scalar_one_or_none()
        
        # Get meals for today
        meals_result = await db.execute(
            select(MealEntry).where(
                and_(
                    MealEntry.user_id == user.id,
                    MealEntry.entry_date == today
                )
            ).order_by(MealEntry.meal_time)
        )
        meals = meals_result.scalars().all()
    
    if not entry:
        await message.answer(
            f"📅 <b>Сегодня ({today.strftime('%Y-%m-%d')})</b>\n\n"
            f"Данных пока нет. Внеси свой дневник!",
            parse_mode="HTML"
        )
        return
    
    # Format report
    report = _format_day_report(entry, today, meals)
    await message.answer(report, parse_mode="HTML")


@router.message(Command("yesterday"))
async def cmd_yesterday(message: Message, user_id: int = None):
    """Show yesterday's summary"""
    if user_id is None:
        user_id = message.from_user.id
    
    # Check access
    user, has_access, error_msg = await check_user_access(user_id)
    if not has_access:
        await message.answer(error_msg)
        return
    
    yesterday = date.today() - timedelta(days=1)
    
    async with get_db() as db:
        result = await db.execute(
            select(User).where(User.telegram_user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer("Используй /start для начала работы")
            return
        
        result = await db.execute(
            select(DayEntry).where(
                and_(
                    DayEntry.user_id == user.id,
                    DayEntry.entry_date == yesterday
                )
            )
        )
        entry = result.scalar_one_or_none()
        
        # Get meals for yesterday
        meals_result = await db.execute(
            select(MealEntry).where(
                and_(
                    MealEntry.user_id == user.id,
                    MealEntry.entry_date == yesterday
                )
            ).order_by(MealEntry.meal_time)
        )
        meals = meals_result.scalars().all()
    
    if not entry:
        await message.answer(
            f"📅 <b>Вчера ({yesterday.strftime('%Y-%m-%d')})</b>\n\n"
            f"Нет данных за этот день.",
            parse_mode="HTML"
        )
        return
    
    report = _format_day_report(entry, yesterday, meals)
    await message.answer(report, parse_mode="HTML")


@router.message(Command("week"))
async def cmd_week(message: Message):
    """Show week summary"""
    user_id = message.from_user.id
    
    # Check access
    user, has_access, error_msg = await check_user_access(user_id)
    if not has_access:
        await message.answer(error_msg)
        return
    
    end_date = date.today()
    start_date = end_date - timedelta(days=6)
    
    async with get_db() as db:
        result = await db.execute(
            select(User).where(User.telegram_user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer("Используй /start для начала работы")
            return
        
        # Get entries for the week
        result = await db.execute(
            select(DayEntry).where(
                and_(
                    DayEntry.user_id == user.id,
                    DayEntry.entry_date >= start_date,
                    DayEntry.entry_date <= end_date
                )
            ).order_by(DayEntry.entry_date)
        )
        entries = result.scalars().all()
    
    if not entries:
        await message.answer(
            f"📊 <b>Неделя ({start_date.strftime('%d.%m')} - {end_date.strftime('%d.%m')})</b>\n\n"
            f"Нет данных за этот период.",
            parse_mode="HTML"
        )
        return
    
    # Calculate averages
    report = _format_week_report(entries, start_date, end_date)
    await message.answer(report, parse_mode="HTML")


def _format_day_report(entry: DayEntry, day: date, meals: list = None) -> str:
    """Format single day report"""
    report = f"📅 <b>{day.strftime('%d.%m.%Y')}</b>\n\n"
    
    # Body metrics
    if entry.weight or entry.waist:
        report += "📏 <b>Параметры:</b>\n"
        if entry.weight:
            report += f"  Вес: {entry.weight} кг\n"
        if entry.waist:
            report += f"  Талия: {entry.waist} см\n"
        report += "\n"
    
    # Sleep
    if entry.sleep_hours:
        report += f"😴 <b>Сон:</b> {format_sleep_time(entry.sleep_hours)}\n\n"
    
    # Activity
    if entry.steps or entry.workout_type:
        report += "🏃 <b>Активность:</b>\n"
        if entry.steps:
            report += f"  Шаги: {entry.steps:,}\n"
            if entry.kcal_steps:
                report += f"  └─ {entry.kcal_steps:.0f} ккал\n"
        if entry.workout_type:
            workout_name = {
                'gym': 'Зал',
                'swimming': 'Плавание',
                'running': 'Бег',
                'cycling': 'Велосипед',
                'other': 'Другое'
            }.get(entry.workout_type.value, entry.workout_type.value)
            report += f"  Тренировка: {workout_name}"
            if entry.workout_minutes:
                report += f" ({entry.workout_minutes} мин)\n"
            else:
                report += "\n"
            if entry.kcal_workout:
                report += f"  └─ {entry.kcal_workout:.0f} ккал\n"
        report += "\n"
    
    # Meals breakdown
    if meals:
        report += "🍽 <b>Питание:</b>\n"
        
        meal_icons = {
            MealType.BREAKFAST: "🍳",
            MealType.LUNCH: "🍲",
            MealType.DINNER: "🍽",
            MealType.SNACK: "🍪"
        }
        
        meal_names = {
            MealType.BREAKFAST: "Завтрак",
            MealType.LUNCH: "Обед",
            MealType.DINNER: "Ужин",
            MealType.SNACK: "Перекус"
        }
        
        for meal in meals:
            icon = meal_icons.get(meal.meal_type, "🍽")
            name = meal_names.get(meal.meal_type, "Еда")
            time_str = f" в {meal.meal_time}" if meal.meal_time else ""
            
            report += f"\n{icon} <b>{name}{time_str}:</b>\n"
            if meal.food_description:
                # Show full description (no truncation)
                report += f"  {meal.food_description}\n"
            
            if meal.kcal:
                report += f"  ✨ {meal.kcal:.0f} ккал"
                if meal.protein or meal.fat or meal.carbs:
                    report += f" | Б:{meal.protein or 0:.0f} Ж:{meal.fat or 0:.0f} У:{meal.carbs or 0:.0f}"
                report += "\n"
        
        report += "\n"
    
    # Calories
    report += "🔥 <b>Калории:</b>\n"
    if entry.bmr:
        report += f"  BMR: {entry.bmr:.0f} ккал\n"
    if entry.kcal_burned_total:
        report += f"  <b>Расход всего: {entry.kcal_burned_total:.0f} ккал</b>\n"
    report += "\n"
    
    if entry.kcal_eaten:
        report += f"  <b>Съедено всего: {entry.kcal_eaten:.0f} ккал</b>\n"
        if entry.protein or entry.fat or entry.carbs:
            report += f"  БЖУ: {entry.protein or 0:.0f}/{entry.fat or 0:.0f}/{entry.carbs or 0:.0f}\n"
    
    # Balance
    if entry.kcal_balance is not None:
        balance_emoji = "🟢" if entry.kcal_balance < -200 else "🟡" if entry.kcal_balance < 200 else "🔴"
        report += f"\n{balance_emoji} <b>Баланс: {format_calories(entry.kcal_balance)} ккал</b>"
        if entry.kcal_balance < -500:
            report += " (большой дефицит)"
        elif entry.kcal_balance > 500:
            report += " (профицит)"
    
    # Notes
    if entry.notes:
        report += f"\n\n💬 {entry.notes}"
    
    return report


def _format_week_report(entries: list, start_date: date, end_date: date) -> str:
    """Format week summary report"""
    report = f"📊 <b>Неделя ({start_date.strftime('%d.%m')} - {end_date.strftime('%d.%m')})</b>\n\n"
    
    total_entries = len(entries)
    report += f"📝 Записей: {total_entries} из 7 дней\n\n"
    
    # Calculate averages
    weights = [e.weight for e in entries if e.weight]
    sleep_hours = [e.sleep_hours for e in entries if e.sleep_hours]
    steps = [e.steps for e in entries if e.steps]
    burned = [e.kcal_burned_total for e in entries if e.kcal_burned_total]
    eaten = [e.kcal_eaten for e in entries if e.kcal_eaten]
    balances = [e.kcal_balance for e in entries if e.kcal_balance is not None]
    workouts = [e for e in entries if e.workout_type]
    
    report += "📈 <b>Средние значения:</b>\n"
    
    if weights:
        avg_weight = sum(weights) / len(weights)
        weight_change = weights[-1] - weights[0] if len(weights) > 1 else 0
        report += f"  Вес: {avg_weight:.1f} кг"
        if weight_change != 0:
            report += f" ({format_calories(weight_change)} кг)\n"
        else:
            report += "\n"
    
    if sleep_hours:
        avg_sleep = sum(sleep_hours) / len(sleep_hours)
        report += f"  Сон: {format_sleep_time(avg_sleep)}\n"
    
    if steps:
        avg_steps = sum(steps) / len(steps)
        report += f"  Шаги: {avg_steps:,.0f}\n"
    
    report += "\n"
    
    if eaten and burned:
        avg_eaten = sum(eaten) / len(eaten)
        avg_burned = sum(burned) / len(burned)
        avg_balance = sum(balances) / len(balances) if balances else 0
        
        report += "🔥 <b>Калории (среднее):</b>\n"
        report += f"  Съедено: {avg_eaten:.0f} ккал\n"
        report += f"  Расход: {avg_burned:.0f} ккал\n"
        report += f"  <b>Баланс: {format_calories(avg_balance)} ккал</b>\n\n"
    
    if workouts:
        report += f"💪 <b>Тренировок:</b> {len(workouts)}\n"
    
    return report


# Callback handlers for menu integration
@router.callback_query(F.data == "stats_today")
async def callback_stats_today(callback: CallbackQuery):
    """Show today's summary via callback"""
    await callback.answer()
    await cmd_today(callback.message, user_id=callback.from_user.id)


@router.callback_query(F.data == "stats_yesterday")
async def callback_stats_yesterday(callback: CallbackQuery):
    """Show yesterday's summary via callback"""
    await callback.answer()
    await cmd_yesterday(callback.message, user_id=callback.from_user.id)


@router.callback_query(F.data == "stats_week")
async def callback_stats_week(callback: CallbackQuery):
    """Show week summary via callback"""
    await callback.answer()
    await cmd_week(callback.message)


@router.callback_query(F.data == "stats_export")
async def callback_stats_export(callback: CallbackQuery):
    """Export data via callback"""
    await callback.answer()
    await cmd_export(callback.message)
