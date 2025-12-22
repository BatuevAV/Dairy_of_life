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


@router.message(Command("breakfast"))
async def cmd_breakfast(message: Message):
    """Generate breakfast suggestions"""
    user_id = message.from_user.id
    
    # Check access
    user, has_access, error_msg = await check_user_access(user_id)
    if not has_access:
        await message.answer(error_msg)
        return
    
    await message.answer("🍳 Генерирую варианты завтрака для тебя...")
    
    try:
        provider = RecommendationsProvider()
        suggestions = await provider.generate_breakfast_suggestions(user, count=3)
        
        text = "🍳 <b>Варианты завтрака:</b>\n\n"
        
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
