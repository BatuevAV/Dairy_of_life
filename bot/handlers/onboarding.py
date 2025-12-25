"""
Onboarding handler - initial profile setup for new users
"""
import logging
from datetime import date
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import update, select

logger = logging.getLogger(__name__)

from bot.database import get_db, User, DayEntry
from bot.ai.recommendations_provider import RecommendationsProvider
from bot.keyboards import get_main_keyboard

router = Router()


class OnboardingStates(StatesGroup):
    """FSM states for onboarding flow"""
    waiting_for_gender = State()
    waiting_for_age = State()
    waiting_for_height = State()
    waiting_for_weight = State()
    waiting_for_goal = State()
    waiting_for_medical = State()


@router.message(Command("onboarding"))
async def cmd_onboarding(message: Message, state: FSMContext):
    """Manually start onboarding process - for testing or re-setup"""
    user_id = message.from_user.id
    
    # Get user from database
    async with get_db() as db:
        result = await db.execute(
            select(User).where(User.telegram_user_id == user_id)
        )
        user = result.scalar_one_or_none()
    
    if not user:
        await message.answer("❌ Сначала используйте /start для регистрации")
        return
    
    await message.answer(
        "🔄 <b>Начинаем заново настройку профиля</b>\n\n"
        "Это перезапишет текущие данные.",
        parse_mode="HTML"
    )
    
    await start_onboarding(message, state, user)


async def start_onboarding(message: Message, state: FSMContext, user: User):
    """Start onboarding process for new user"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👨 Мужской", callback_data="gender_male"),
            InlineKeyboardButton(text="👩 Женский", callback_data="gender_female")
        ]
    ])
    
    await message.answer(
        "👋 <b>Давай настроим твой профиль!</b>\n\n"
        "Это займет всего минуту и поможет мне давать точные рекомендации.\n\n"
        "🚻 <b>Выбери свой пол:</b>",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await state.set_state(OnboardingStates.waiting_for_gender)


@router.callback_query(F.data.startswith("gender_"), OnboardingStates.waiting_for_gender)
async def process_gender(callback: CallbackQuery, state: FSMContext):
    """Process gender selection"""
    await callback.answer()
    
    gender = "male" if callback.data == "gender_male" else "female"
    await state.update_data(gender=gender)
    
    gender_emoji = "👨" if gender == "male" else "👩"
    
    await callback.message.edit_text(
        f"{gender_emoji} <b>Отлично!</b>\n\n"
        "🎂 <b>Сколько тебе лет?</b>\n\n"
        "Напиши число (например: 25)",
        parse_mode="HTML"
    )
    await state.set_state(OnboardingStates.waiting_for_age)


@router.message(OnboardingStates.waiting_for_age, F.text)
async def process_age(message: Message, state: FSMContext):
    """Process age input"""
    try:
        age = int(message.text.strip())
        if age < 10 or age > 120:
            await message.answer("❌ Введи корректный возраст (10-120 лет)")
            return
        
        await state.update_data(age=age)
        
        await message.answer(
            "✅ <b>Принято!</b>\n\n"
            "📏 <b>Какой у тебя рост?</b>\n\n"
            "Укажи в сантиметрах (например: 175)",
            parse_mode="HTML"
        )
        await state.set_state(OnboardingStates.waiting_for_height)
        
    except ValueError:
        await message.answer("❌ Введи возраст числом (например: 25)")


@router.message(OnboardingStates.waiting_for_height, F.text)
async def process_height(message: Message, state: FSMContext):
    """Process height input"""
    try:
        height = int(message.text.strip())
        if height < 100 or height > 250:
            await message.answer("❌ Введи корректный рост (100-250 см)")
            return
        
        await state.update_data(height=height)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_weight")]
        ])
        
        await message.answer(
            "✅ <b>Отлично!</b>\n\n"
            "⚖️ <b>Какой у тебя вес?</b> (опционально)\n\n"
            "Укажи в килограммах (например: 70)\n"
            "Или пропусти этот шаг",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        await state.set_state(OnboardingStates.waiting_for_weight)
        
    except ValueError:
        await message.answer("❌ Введи рост числом (например: 175)")


@router.message(OnboardingStates.waiting_for_weight, F.text)
async def process_weight(message: Message, state: FSMContext):
    """Process weight input"""
    try:
        weight = float(message.text.strip().replace(',', '.'))  # Support both dot and comma
        if weight < 30 or weight > 300:
            await message.answer("❌ Введи корректный вес (30-300 кг)")
            return
        
        await state.update_data(weight=weight)
        await ask_goal(message, state)
        
    except ValueError:
        await message.answer("❌ Введи вес числом (например: 70 или 69.6)")


@router.callback_query(F.data == "skip_weight", OnboardingStates.waiting_for_weight)
async def skip_weight(callback: CallbackQuery, state: FSMContext):
    """Skip weight input"""
    await callback.answer()
    # Remove keyboard to show action was processed
    await callback.message.edit_reply_markup(reply_markup=None)
    await ask_goal(callback.message, state)


async def ask_goal(message: Message, state: FSMContext):
    """Ask user about their goal"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💪 Набрать мышечную массу", callback_data="goal_gain")],
        [InlineKeyboardButton(text="⚖️ Поддерживать вес", callback_data="goal_maintain")],
        [InlineKeyboardButton(text="🔥 Снизить вес", callback_data="goal_lose")],
        [InlineKeyboardButton(text="🏃 Улучшить выносливость", callback_data="goal_endurance")],
        [InlineKeyboardButton(text="✍️ Ввести свою цель", callback_data="goal_custom")],
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_goal")]
    ])
    
    await message.answer(
        "🎯 <b>Какая у тебя цель?</b>\n\n"
        "Выбери из списка или напиши свою цель:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await state.set_state(OnboardingStates.waiting_for_goal)


@router.callback_query(F.data.startswith("goal_"), OnboardingStates.waiting_for_goal)
async def process_goal(callback: CallbackQuery, state: FSMContext):
    """Process goal selection"""
    await callback.answer()
    
    goal_map = {
        "goal_gain": "Набрать мышечную массу",
        "goal_maintain": "Поддерживать текущий вес",
        "goal_lose": "Снизить вес",
        "goal_endurance": "Улучшить выносливость"
    }
    
    if callback.data == "skip_goal":
        # Remove keyboard to show action was processed
        await callback.message.edit_reply_markup(reply_markup=None)
        await ask_medical(callback.message, state)
        return
    
    if callback.data == "goal_custom":
        await callback.message.edit_text(
            "✍️ <b>Напиши свою цель</b>\n\n"
            "Например:\n"
            "• Набрать мышечную массу и убрать живот\n"
            "• Подготовиться к марафону\n"
            "• Восстановить режим после отпуска",
            parse_mode="HTML"
        )
        return
    
    goal = goal_map.get(callback.data, "")
    await state.update_data(goal=goal)
    # Remove keyboard to show action was processed
    await callback.message.edit_reply_markup(reply_markup=None)
    await ask_medical(callback.message, state)


@router.message(OnboardingStates.waiting_for_goal, F.text)
async def process_goal_text(message: Message, state: FSMContext):
    """Process custom goal text input"""
    goal = message.text.strip()
    
    if len(goal) < 5:
        await message.answer("❌ Опиши цель подробнее (минимум 5 символов)")
        return
    
    await state.update_data(goal=goal)
    
    await message.answer(
        f"✅ <b>Цель принята:</b>\n{goal}",
        parse_mode="HTML"
    )
    
    await ask_medical(message, state)


async def ask_medical(message: Message, state: FSMContext):
    """Ask about medical recommendations"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Нет ограничений", callback_data="skip_medical")]
    ])
    
    await message.answer(
        "🏥 <b>Есть ли у тебя медицинские ограничения?</b>\n\n"
        "Например:\n"
        "• Аллергия на продукты\n"
        "• Ограничения по нагрузкам\n"
        "• Рекомендации врача\n\n"
        "Опиши кратко или нажми кнопку, если нет ограничений:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await state.set_state(OnboardingStates.waiting_for_medical)


@router.message(OnboardingStates.waiting_for_medical, F.text)
async def process_medical(message: Message, state: FSMContext):
    """Process medical recommendations input"""
    medical = message.text.strip()
    await state.update_data(medical_recommendations=medical)
    await complete_onboarding(message, state)


@router.callback_query(F.data == "skip_medical", OnboardingStates.waiting_for_medical)
async def skip_medical(callback: CallbackQuery, state: FSMContext):
    """Skip medical recommendations"""
    await callback.answer()
    # Remove keyboard to show action was processed
    await callback.message.edit_reply_markup(reply_markup=None)
    await complete_onboarding(callback.message, state)


async def complete_onboarding(message: Message, state: FSMContext):
    """Complete onboarding and save profile"""
    user_id = message.from_user.id
    data = await state.get_data()
    
    # Update user profile
    update_data = {
        "gender": data.get("gender", "male"),
        "age": data.get("age", 28),
        "height": data.get("height", 179),
        "profile_completed": True
    }
    
    if data.get("goal"):
        update_data["goal"] = data["goal"]
    
    if data.get("medical_recommendations"):
        update_data["medical_recommendations"] = data["medical_recommendations"]
    
    # Update user in database - first check if user exists
    async with get_db() as db:
        result = await db.execute(
            select(User).where(User.telegram_user_id == user_id)
        )
        existing_user = result.scalar_one_or_none()
        
        if not existing_user:
            # User doesn't exist, this shouldn't happen but handle gracefully
            logger.error(f"User {user_id} not found during onboarding completion")
            await message.answer(
                "❌ Пользователь не найден. Пожалуйста, начните с команды /start"
            )
            await state.clear()
            return
        
        logger.info(f"Completing onboarding for user {user_id} with data: {update_data}")
        
        # Update user
        await db.execute(
            update(User)
            .where(User.telegram_user_id == user_id)
            .values(**update_data)
        )
        await db.commit()
        logger.info(f"Profile updated successfully for user {user_id}")
    
    # Save weight to today's DayEntry if provided
    if data.get("weight"):
        async with get_db() as db:
            today = date.today()
            result = await db.execute(
                select(User).where(User.telegram_user_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                # User not found, skip weight saving
                pass
            else:
                # Check if today's entry exists
                result = await db.execute(
                    select(DayEntry).where(
                        DayEntry.user_id == user.id,
                        DayEntry.entry_date == today
                    )
                )
                day_entry = result.scalar_one_or_none()
                
                if day_entry:
                    # Update existing entry
                    await db.execute(
                        update(DayEntry)
                        .where(DayEntry.id == day_entry.id)
                        .values(weight=data["weight"])
                    )
                else:
                    # Create new entry with weight
                    new_entry = DayEntry(
                        user_id=user.id,
                        entry_date=today,
                        weight=data["weight"]
                    )
                    db.add(new_entry)
                
                await db.commit()
    
    # Get updated user for AI recommendations
    async with get_db() as db:
        result = await db.execute(
            select(User).where(User.telegram_user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            logger.error(f"User {user_id} not found after profile update")
            await message.answer(
                "❌ Ошибка при получении профиля. Попробуйте /start еще раз."
            )
            await state.clear()
            return
    
    await state.clear()
    
    # Show profile completion message
    profile_summary = f"👤 <b>Профиль успешно создан!</b>\n\n"
    profile_summary += f"📊 <b>Твои данные:</b>\n"
    profile_summary += f"• Пол: {'Мужской' if data.get('gender') == 'male' else 'Женский'}\n"
    profile_summary += f"• Возраст: {data.get('age', 'не указан')} лет\n"
    profile_summary += f"• Рост: {data.get('height', 'не указан')} см\n"
    
    if data.get('weight'):
        profile_summary += f"• Вес: {data.get('weight')} кг\n"
    
    if data.get('goal'):
        profile_summary += f"• Цель: {data.get('goal')}\n"
    
    await message.answer(profile_summary, parse_mode="HTML")
    
    # Generate AI recommendation
    await message.answer(
        "⏳ Генерирую персональные рекомендации...",
        parse_mode="HTML"
    )
    
    try:
        provider = RecommendationsProvider()
        brief_rec = await provider.generate_brief_recommendation(user)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🥗 Подробно о питании", callback_data="detailed_nutrition")],
            [InlineKeyboardButton(text="💪 Подробно о тренировках", callback_data="detailed_workout")],
            [InlineKeyboardButton(text="📝 Начать использовать", callback_data="start_using")]
        ])
        
        await message.answer(
            f"💡 <b>Персональная рекомендация:</b>\n\n{brief_rec}\n\n"
            "Хочешь узнать больше?",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        
        # Show main keyboard in next message
        await message.answer(
            "Используй кнопку <b>📋 Меню</b> внизу для быстрого доступа к функциям!",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        await message.answer(
            "✅ <b>Готово!</b>\n\n"
            "Используй команды для работы с дневником:\n"
            "/today - Сводка за сегодня\n"
            "/menu - Главное меню\n"
            "/help - Справка",
            parse_mode="HTML",
            reply_markup=get_main_keyboard()
        )


@router.callback_query(F.data == "start_using")
async def start_using(callback: CallbackQuery):
    """Show main commands after onboarding"""
    await callback.answer()
    await callback.message.answer(
        "🎉 <b>Отлично! Теперь ты готов к работе</b>\n\n"
        "📝 <b>Основные команды:</b>\n"
        "/menu - Главное меню\n"
        "/today - Сводка за сегодня\n"
        "/breakfast - Идеи завтрака\n"
        "/help - Полная справка\n\n"
        "📸 <b>Просто отправь фото еды</b> - я распознаю и посчитаю калории!\n\n"
        "Или напиши что съел текстом - я оценю калорийность.",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )
