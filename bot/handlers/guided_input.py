"""
Guided input handler - step-by-step diary entry
"""
from datetime import date
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.sql import and_

from bot.config import settings
from bot.database import get_db, User, DayEntry, WorkoutType
from bot.calculations import update_day_entry_calculations
from bot.utils import get_today_in_timezone

router = Router()


class GuidedEntry(StatesGroup):
    """States for guided entry"""
    date = State()
    weight = State()
    waist = State()
    sleep = State()
    steps = State()
    workout_type = State()
    workout_minutes = State()
    calories = State()
    confirm = State()


@router.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext):
    """Start guided entry"""
    user_id = message.from_user.id
    
    if user_id != settings.OWNER_TELEGRAM_ID:
        return
    
    # Check if user has guided mode
    async with get_db() as db:
        result = await db.execute(
            select(User).where(User.telegram_user_id == user_id)
        )
        user = result.scalar_one_or_none()
    
    if not user:
        await message.answer("Используй /start для начала работы")
        return
    
    # Initialize entry data
    await state.update_data(user_db_id=user.id)
    
    # Ask for date
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Сегодня")],
            [KeyboardButton(text="Вчера")]
        ],
        resize_keyboard=True
    )
    
    await message.answer(
        "📅 Выбери дату записи:",
        reply_markup=keyboard
    )
    await state.set_state(GuidedEntry.date)


@router.message(GuidedEntry.date)
async def process_date(message: Message, state: FSMContext):
    """Process date input"""
    text = message.text.lower()
    
    if text == "сегодня":
        entry_date = date.today()
    elif text == "вчера":
        from datetime import timedelta
        entry_date = date.today() - timedelta(days=1)
    else:
        # Try to parse date
        from bot.utils import parse_date as parse_date_func
        entry_date = parse_date_func(text)
        if not entry_date:
            await message.answer("❌ Не понял дату. Попробуй ещё раз или выбери кнопкой.")
            return
    
    await state.update_data(entry_date=entry_date)
    
    # Ask for weight
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Пропустить")]],
        resize_keyboard=True
    )
    
    await message.answer(
        f"✅ Дата: {entry_date.strftime('%d.%m.%Y')}\n\n"
        f"⚖️ Введи вес (в кг) или нажми \"Пропустить\":",
        reply_markup=keyboard
    )
    await state.set_state(GuidedEntry.weight)


@router.message(GuidedEntry.weight)
async def process_weight(message: Message, state: FSMContext):
    """Process weight input"""
    text = message.text.lower()
    
    weight = None
    if text != "пропустить":
        try:
            weight = float(text.replace(",", ".").replace("кг", "").strip())
            if not (40 <= weight <= 200):
                await message.answer("❌ Вес должен быть в пределах 40-200 кг. Попробуй ещё раз.")
                return
        except ValueError:
            await message.answer("❌ Не понял число. Введи вес числом или нажми \"Пропустить\".")
            return
    
    await state.update_data(weight=weight)
    
    # Ask for waist
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Пропустить")]],
        resize_keyboard=True
    )
    
    await message.answer(
        "📏 Введи обхват талии (в см) или нажми \"Пропустить\":",
        reply_markup=keyboard
    )
    await state.set_state(GuidedEntry.waist)


@router.message(GuidedEntry.waist)
async def process_waist(message: Message, state: FSMContext):
    """Process waist input"""
    text = message.text.lower()
    
    waist = None
    if text != "пропустить":
        try:
            waist = float(text.replace(",", ".").replace("см", "").strip())
            if not (50 <= waist <= 150):
                await message.answer("❌ Талия должна быть в пределах 50-150 см. Попробуй ещё раз.")
                return
        except ValueError:
            await message.answer("❌ Не понял число. Введи талию числом или нажми \"Пропустить\".")
            return
    
    await state.update_data(waist=waist)
    
    # Ask for sleep
    await message.answer(
        "😴 Введи сон в часах (например: 7.5) или как время (22:30-07:00):",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(GuidedEntry.sleep)


@router.message(GuidedEntry.sleep)
async def process_sleep(message: Message, state: FSMContext):
    """Process sleep input"""
    text = message.text
    
    sleep_hours = None
    
    # Try to parse time range
    if "-" in text or "–" in text:
        from bot.utils import sleep_duration_from_range
        # Extract time range
        import re
        match = re.search(r'(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})', text)
        if match:
            sleep_hours = sleep_duration_from_range(match.group(1), match.group(2))
    
    # Try to parse as hours
    if not sleep_hours:
        try:
            sleep_hours = float(text.replace(",", ".").replace("ч", "").strip())
            if not (0 <= sleep_hours <= 24):
                await message.answer("❌ Сон должен быть в пределах 0-24 часов. Попробуй ещё раз.")
                return
        except ValueError:
            await message.answer("❌ Не понял. Введи часы числом (например: 7.5) или время (22:30-07:00).")
            return
    
    await state.update_data(sleep_hours=sleep_hours)
    
    # Ask for steps
    await message.answer("🚶 Введи количество шагов:")
    await state.set_state(GuidedEntry.steps)


@router.message(GuidedEntry.steps)
async def process_steps(message: Message, state: FSMContext):
    """Process steps input"""
    text = message.text
    
    try:
        steps = int(text.replace(",", "").replace(" ", "").strip())
        if not (0 <= steps <= 100000):
            await message.answer("❌ Количество шагов должно быть в пределах 0-100000. Попробуй ещё раз.")
            return
    except ValueError:
        await message.answer("❌ Не понял число. Введи количество шагов.")
        return
    
    await state.update_data(steps=steps)
    
    # Ask for workout type
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏋️ Зал", callback_data="workout_gym"),
            InlineKeyboardButton(text="🏊 Плавание", callback_data="workout_swimming")
        ],
        [
            InlineKeyboardButton(text="🏃 Бег", callback_data="workout_running"),
            InlineKeyboardButton(text="🚴 Велосипед", callback_data="workout_cycling")
        ],
        [
            InlineKeyboardButton(text="❌ Нет тренировки", callback_data="workout_none")
        ]
    ])
    
    await message.answer(
        "💪 Была тренировка?",
        reply_markup=keyboard
    )
    await state.set_state(GuidedEntry.workout_type)


@router.callback_query(GuidedEntry.workout_type, F.data.startswith("workout_"))
async def process_workout_type(callback: CallbackQuery, state: FSMContext):
    """Process workout type"""
    workout_str = callback.data.split("_")[1]
    
    if workout_str == "none":
        await state.update_data(workout_type=None, workout_minutes=None)
        await callback.message.edit_text("✅ Без тренировки")
        
        # Ask for calories
        await callback.message.answer("🍽 Введи съеденные калории за день:")
        await state.set_state(GuidedEntry.calories)
    else:
        workout_type = WorkoutType[workout_str.upper()]
        await state.update_data(workout_type=workout_type)
        
        workout_names = {
            "gym": "Зал",
            "swimming": "Плавание",
            "running": "Бег",
            "cycling": "Велосипед"
        }
        
        await callback.message.edit_text(f"✅ Тренировка: {workout_names[workout_str]}")
        await callback.message.answer("⏱ Введи длительность тренировки в минутах:")
        await state.set_state(GuidedEntry.workout_minutes)
    
    await callback.answer()


@router.message(GuidedEntry.workout_minutes)
async def process_workout_minutes(message: Message, state: FSMContext):
    """Process workout minutes"""
    text = message.text
    
    try:
        minutes = int(text.replace("мин", "").strip())
        if not (1 <= minutes <= 600):
            await message.answer("❌ Длительность должна быть в пределах 1-600 минут. Попробуй ещё раз.")
            return
    except ValueError:
        await message.answer("❌ Не понял число. Введи минуты.")
        return
    
    await state.update_data(workout_minutes=minutes)
    
    # Ask for calories
    await message.answer("🍽 Введи съеденные калории за день:")
    await state.set_state(GuidedEntry.calories)


@router.message(GuidedEntry.calories)
async def process_calories(message: Message, state: FSMContext):
    """Process calories"""
    text = message.text
    
    try:
        calories = float(text.replace(",", ".").replace("ккал", "").strip())
        if not (0 <= calories <= 10000):
            await message.answer("❌ Калории должны быть в пределах 0-10000. Попробуй ещё раз.")
            return
    except ValueError:
        await message.answer("❌ Не понял число. Введи калории.")
        return
    
    await state.update_data(kcal_eaten=calories)
    
    # Show summary and ask for confirmation
    data = await state.get_data()
    summary = _format_entry_summary(data)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Сохранить", callback_data="guided_save"),
            InlineKeyboardButton(text="❌ Отменить", callback_data="guided_cancel")
        ]
    ])
    
    await message.answer(
        f"📝 <b>Проверь данные:</b>\n\n{summary}",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await state.set_state(GuidedEntry.confirm)


@router.callback_query(GuidedEntry.confirm, F.data == "guided_save")
async def save_entry(callback: CallbackQuery, state: FSMContext):
    """Save entry to database"""
    data = await state.get_data()
    
    async with get_db() as db:
        # Get user
        user_id = data['user_db_id']
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()
        
        # Check if entry exists
        entry_date = data['entry_date']
        result = await db.execute(
            select(DayEntry).where(
                and_(
                    DayEntry.user_id == user_id,
                    DayEntry.entry_date == entry_date
                )
            )
        )
        entry = result.scalar_one_or_none()
        
        if entry:
            # Update existing
            entry.weight = data.get('weight')
            entry.waist = data.get('waist')
            entry.sleep_hours = data.get('sleep_hours')
            entry.steps = data.get('steps')
            entry.workout_type = data.get('workout_type')
            entry.workout_minutes = data.get('workout_minutes')
            entry.kcal_eaten = data.get('kcal_eaten')
        else:
            # Create new
            entry = DayEntry(
                user_id=user_id,
                entry_date=entry_date,
                weight=data.get('weight'),
                waist=data.get('waist'),
                sleep_hours=data.get('sleep_hours'),
                steps=data.get('steps'),
                workout_type=data.get('workout_type'),
                workout_minutes=data.get('workout_minutes'),
                kcal_eaten=data.get('kcal_eaten')
            )
            db.add(entry)
        
        # Calculate fields
        entry = update_day_entry_calculations(entry, user)
        
        await db.commit()
    
    await callback.message.edit_text("✅ Запись сохранена!")
    await callback.message.answer(
        "Используй /today для просмотра сводки.\n"
        "Или /add чтобы добавить ещё запись.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    await state.clear()
    await callback.answer()


@router.callback_query(GuidedEntry.confirm, F.data == "guided_cancel")
async def cancel_entry(callback: CallbackQuery, state: FSMContext):
    """Cancel entry"""
    await callback.message.edit_text("❌ Запись отменена")
    await state.clear()
    await callback.answer()


def _format_entry_summary(data: dict) -> str:
    """Format entry summary for confirmation"""
    summary = f"📅 Дата: {data['entry_date'].strftime('%d.%m.%Y')}\n"
    
    if data.get('weight'):
        summary += f"⚖️ Вес: {data['weight']} кг\n"
    if data.get('waist'):
        summary += f"📏 Талия: {data['waist']} см\n"
    if data.get('sleep_hours'):
        summary += f"😴 Сон: {data['sleep_hours']:.1f} ч\n"
    if data.get('steps'):
        summary += f"🚶 Шаги: {data['steps']:,}\n"
    if data.get('workout_type'):
        workout_names = {
            WorkoutType.GYM: "Зал",
            WorkoutType.SWIMMING: "Плавание",
            WorkoutType.RUNNING: "Бег",
            WorkoutType.CYCLING: "Велосипед"
        }
        summary += f"💪 Тренировка: {workout_names[data['workout_type']]} ({data.get('workout_minutes', 0)} мин)\n"
    if data.get('kcal_eaten'):
        summary += f"🍽 Калории: {data['kcal_eaten']:.0f} ккал\n"
    
    return summary
