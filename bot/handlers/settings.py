"""
Settings handler - /settings command
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, update

from bot.config import settings
from bot.database import get_db, User
from bot.utils import check_user_access

router = Router()


class UpdateProfile(StatesGroup):
    """States for updating profile"""
    field = State()
    value = State()


@router.message(Command("settings"))
async def cmd_settings(message: Message):
    """Handle /settings command"""
    user_id = message.from_user.id
    
    # Check access
    user, has_access, error_msg = await check_user_access(user_id)
    if not has_access:
        await message.answer(error_msg)
        return
    
    # Get user profile
    async with get_db() as db:
        result = await db.execute(
            select(User).where(User.telegram_user_id == user_id)
        )
        user = result.scalar_one_or_none()
    
    if not user:
        await message.answer("Используй /start для начала работы")
        return
    
    # Format settings
    settings_text = (
        "⚙️ <b>Настройки профиля</b>\n\n"
        "<b>Параметры:</b>\n"
        f"  Пол: {'Мужской' if user.gender == 'male' else 'Женский'}\n"
        f"  Возраст: {user.age} лет\n"
        f"  Рост: {user.height} см\n\n"
        "<b>Коэффициенты расчёта:</b>\n"
        f"  Ккал на шаг: {user.step_kcal_coef}\n"
        f"  Зал (ккал/час): {user.gym_kcal_per_hour}\n"
        f"  Плавание (ккал/час): {user.swim_kcal_per_hour}\n"
        f"  Бег (ккал/час): {user.running_kcal_per_hour}\n"
        f"  Велосипед (ккал/час): {user.cycling_kcal_per_hour}\n\n"
        f"  Часовой пояс: {user.timezone}\n"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить возраст", callback_data="edit_age")],
        [InlineKeyboardButton(text="✏️ Изменить рост", callback_data="edit_height")],
        [InlineKeyboardButton(text="✏️ Изменить ккал/шаг", callback_data="edit_step_coef")],
        [InlineKeyboardButton(text="✏️ Изменить ккал зал", callback_data="edit_gym_kcal")],
    ])
    
    await message.answer(settings_text, parse_mode="HTML", reply_markup=keyboard)


@router.callback_query(F.data.startswith("edit_"))
async def callback_edit_setting(callback: CallbackQuery, state: FSMContext):
    """Handle edit setting callback"""
    field = callback.data.split("_", 1)[1]
    
    field_names = {
        'age': ('возраст', 'лет', 'age'),
        'height': ('рост', 'см', 'height'),
        'step_coef': ('коэффициент ккал/шаг', 'ккал/шаг', 'step_kcal_coef'),
        'gym_kcal': ('ккал зал (в час)', 'ккал/час', 'gym_kcal_per_hour'),
    }
    
    if field not in field_names:
        await callback.answer("Неизвестное поле")
        return
    
    field_name, unit, db_field = field_names[field]
    
    await state.update_data(edit_field=db_field, field_name=field_name, unit=unit)
    
    await callback.message.answer(
        f"✏️ Введи новое значение для <b>{field_name}</b> ({unit}):",
        parse_mode="HTML"
    )
    
    await state.set_state(UpdateProfile.value)
    await callback.answer()


@router.message(UpdateProfile.value)
async def process_setting_value(message: Message, state: FSMContext):
    """Process new setting value"""
    user_id = message.from_user.id
    
    # Check access
    user, has_access, error_msg = await check_user_access(user_id)
    if not has_access:
        await message.answer(error_msg)
        await state.clear()
        return
    
    data = await state.get_data()
    field = data['edit_field']
    field_name = data['field_name']
    
    # Parse value
    try:
        if field in ['age', 'height']:
            value = int(message.text.strip())
        else:
            value = float(message.text.replace(',', '.').strip())
        
        # Validate
        if field == 'age' and not (10 <= value <= 100):
            await message.answer("❌ Возраст должен быть в пределах 10-100 лет.")
            return
        if field == 'height' and not (100 <= value <= 250):
            await message.answer("❌ Рост должен быть в пределах 100-250 см.")
            return
        if field in ['step_kcal_coef', 'gym_kcal_per_hour'] and not (0 < value < 10000):
            await message.answer("❌ Значение должно быть положительным и разумным.")
            return
    except ValueError:
        await message.answer("❌ Не понял число. Попробуй ещё раз.")
        return
    
    # Update in database
    async with get_db() as db:
        await db.execute(
            update(User)
            .where(User.telegram_user_id == user_id)
            .values(**{field: value})
        )
        await db.commit()
    
    await message.answer(f"✅ <b>{field_name.capitalize()}</b> обновлено: {value}", parse_mode="HTML")
    await state.clear()
