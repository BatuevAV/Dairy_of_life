"""
Recipes handler - breakfast suggestions and recipe generation
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from bot.config import settings
from bot.database import get_db, User
from bot.utils import check_user_access
from bot.ai.recommendations_provider import RecommendationsProvider

router = Router()


async def _generate_meal_suggestions_handler(message: Message, meal_type: str):
    """Universal handler for meal suggestions"""
    user_id = message.from_user.id
    
    # Check access
    user, has_access, error_msg = await check_user_access(user_id)
    if not has_access:
        await message.answer(error_msg)
        return
    
    meal_emojis = {
        "breakfast": "🍳",
        "lunch": "🍽",
        "dinner": "🍴",
        "snack": "🥤"
    }
    
    meal_names_ru = {
        "breakfast": "завтрака",
        "lunch": "обеда",
        "dinner": "ужина",
        "snack": "перекуса"
    }
    
    meal_titles_ru = {
        "breakfast": "Варианты завтрака",
        "lunch": "Варианты обеда",
        "dinner": "Варианты ужина",
        "snack": "Варианты перекуса"
    }
    
    emoji = meal_emojis.get(meal_type, "🍽")
    meal_name = meal_names_ru.get(meal_type, "приема пищи")
    title = meal_titles_ru.get(meal_type, "Варианты")
    
    await message.answer(f"{emoji} Генерирую варианты {meal_name} для тебя...")
    
    try:
        provider = RecommendationsProvider()
        suggestions = await provider.generate_meal_suggestions(user, meal_type, count=3)
        
        text = f"{emoji} <b>{title}:</b>\n\n"
        
        keyboard_buttons = []
        for idx, dish in enumerate(suggestions, 1):
            text += (
                f"<b>{idx}. {dish['name']}</b>\n"
                f"   {dish['description']}\n"
                f"   🔥 {dish['kcal']} ккал | "
                f"Б: {dish['protein']}г | Ж: {dish['fat']}г | У: {dish['carbs']}г\n\n"
            )
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"📋 Рецепт: {dish['name']}", 
                    callback_data=f"recipe:{dish['name']}"
                )
            ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при генерации: {str(e)}")


@router.message(Command("breakfast"))
async def cmd_breakfast(message: Message):
    """Generate breakfast suggestions"""
    await _generate_meal_suggestions_handler(message, "breakfast")


@router.message(Command("lunch"))
async def cmd_lunch(message: Message):
    """Generate lunch suggestions"""
    await _generate_meal_suggestions_handler(message, "lunch")


@router.message(Command("dinner"))
async def cmd_dinner(message: Message):
    """Generate dinner suggestions"""
    await _generate_meal_suggestions_handler(message, "dinner")


@router.message(Command("snack"))
async def cmd_snack(message: Message):
    """Generate snack suggestions"""
    await _generate_meal_suggestions_handler(message, "snack")


@router.callback_query(F.data.startswith("recipe:"))
async def callback_show_recipe(callback: CallbackQuery):
    """Show detailed recipe"""
    dish_name = callback.data.split(":", 1)[1]
    
    user_id = callback.from_user.id
    
    # Check access
    user, has_access, error_msg = await check_user_access(user_id)
    if not has_access:
        await callback.answer(error_msg, show_alert=True)
        return
    
    await callback.message.answer(f"📋 Генерирую рецепт для '{dish_name}'...")
    
    try:
        provider = RecommendationsProvider()
        recipe = await provider.generate_recipe(dish_name, user)
        
        # Format recipe
        text = f"📋 <b>{recipe['name']}</b>\n\n"
        text += f"📝 {recipe['description']}\n"
        text += f"👥 Порций: {recipe['servings']}\n"
        text += f"⏱ Время: {recipe['cooking_time']} мин\n\n"
        
        text += "<b>🛒 Продукты:</b>\n"
        for ingredient in recipe['ingredients']:
            text += f"  • {ingredient['item']} - {ingredient['amount']}\n"
        
        text += "\n<b>👨‍🍳 Приготовление:</b>\n"
        for idx, step in enumerate(recipe['instructions'], 1):
            text += f"{idx}. {step}\n"
        
        nutrition = recipe['nutrition']
        text += f"\n<b>📊 Пищевая ценность (на порцию):</b>\n"
        text += f"🔥 {nutrition['kcal']} ккал\n"
        text += f"Белки: {nutrition['protein']}г | Жиры: {nutrition['fat']}г | Углеводы: {nutrition['carbs']}г"
        
        # Split if too long
        if len(text) > 4000:
            # Send in parts
            parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
            for part in parts:
                await callback.message.answer(part, parse_mode="HTML")
        else:
            await callback.message.answer(text, parse_mode="HTML")
        
        await callback.answer()
        
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при генерации рецепта: {str(e)}")
        await callback.answer()


@router.callback_query(F.data == "detailed_nutrition")
async def callback_detailed_nutrition(callback: CallbackQuery):
    """Show detailed nutrition recommendation"""
    user_id = callback.from_user.id
    
    # Check access
    user, has_access, error_msg = await check_user_access(user_id)
    if not has_access:
        await callback.answer(error_msg, show_alert=True)
        return
    
    await callback.message.answer("🥗 Генерирую подробные рекомендации по питанию...")
    
    try:
        provider = RecommendationsProvider()
        recommendation = await provider.generate_detailed_nutrition_recommendation(user)
        
        await callback.message.answer(
            f"🥗 <b>Рекомендации по питанию</b>\n\n{recommendation}",
            parse_mode="HTML"
        )
        await callback.answer()
        
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка: {str(e)}")
        await callback.answer()


@router.callback_query(F.data == "detailed_workout")
async def callback_detailed_workout(callback: CallbackQuery):
    """Show detailed workout recommendation"""
    user_id = callback.from_user.id
    
    # Check access
    user, has_access, error_msg = await check_user_access(user_id)
    if not has_access:
        await callback.answer(error_msg, show_alert=True)
        return
    
    await callback.message.answer("💪 Генерирую подробные рекомендации по тренировкам...")
    
    try:
        provider = RecommendationsProvider()
        recommendation = await provider.generate_detailed_workout_recommendation(user)
        
        await callback.message.answer(
            f"💪 <b>Рекомендации по тренировкам</b>\n\n{recommendation}",
            parse_mode="HTML"
        )
        await callback.answer()
        
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка: {str(e)}")
        await callback.answer()


@router.callback_query(F.data.startswith("meal_"))
async def callback_regenerate_meal(callback: CallbackQuery):
    """Regenerate meal suggestions from notification button"""
    meal_type = callback.data.split("_", 1)[1]
    
    user_id = callback.from_user.id
    
    # Check access
    user, has_access, error_msg = await check_user_access(user_id)
    if not has_access:
        await callback.answer(error_msg, show_alert=True)
        return
    
    meal_emojis = {
        "breakfast": "🍳",
        "lunch": "🍽",
        "dinner": "🍴",
        "snack": "🥤"
    }
    
    meal_names_ru = {
        "breakfast": "завтрака",
        "lunch": "обеда",
        "dinner": "ужина",
        "snack": "перекуса"
    }
    
    meal_titles_ru = {
        "breakfast": "Варианты завтрака",
        "lunch": "Варианты обеда",
        "dinner": "Варианты ужина",
        "snack": "Варианты перекуса"
    }
    
    emoji = meal_emojis.get(meal_type, "🍽")
    meal_name = meal_names_ru.get(meal_type, "приема пищи")
    title = meal_titles_ru.get(meal_type, "Варианты")
    
    await callback.message.answer(f"{emoji} Генерирую новые варианты {meal_name}...")
    
    try:
        provider = RecommendationsProvider()
        suggestions = await provider.generate_meal_suggestions(user, meal_type, count=3)
        
        text = f"{emoji} <b>{title}:</b>\n\n"
        
        keyboard_buttons = []
        for idx, dish in enumerate(suggestions, 1):
            text += (
                f"<b>{idx}. {dish['name']}</b>\n"
                f"   {dish['description']}\n"
                f"   🔥 {dish['kcal']} ккал | "
                f"Б: {dish['protein']}г | Ж: {dish['fat']}г | У: {dish['carbs']}г\n\n"
            )
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"📋 Рецепт: {dish['name']}", 
                    callback_data=f"recipe:{dish['name']}"
                )
            ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при генерации: {str(e)}")
        await callback.answer()

