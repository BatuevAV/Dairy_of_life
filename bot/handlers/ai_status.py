"""
AI Status handler - check AI provider availability and limits
"""
import asyncio
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select

from bot.config import settings
from bot.database import get_db, User
from bot.ai.gemini_provider import GeminiProvider
from bot.ai.ollama_provider import OllamaProvider

router = Router()


@router.message(Command("ai_status"))
async def cmd_ai_status(message: Message):
    """Check AI provider status and availability (owner only)"""
    user_id = message.from_user.id
    
    # Check if user is owner
    async with get_db() as db:
        result = await db.execute(
            select(User).where(User.telegram_user_id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.is_owner:
            await message.answer("❌ Эта команда доступна только владельцу бота")
            return
    
    status_msg = "🤖 **Статус AI провайдеров:**\n\n"
    
    # Check current provider
    current_provider = settings.DEFAULT_AI_PROVIDER
    status_msg += f"📌 **Текущий:** {current_provider}\n\n"
    
    # Test Gemini
    status_msg += "**🟢 Gemini API:**\n"
    try:
        gemini = GeminiProvider()
        # Try a simple test request
        test_result = await asyncio.wait_for(
            gemini.generate_text("Estimate calories in: яблоко"),
            timeout=10
        )
        if test_result and len(test_result) > 0:
            status_msg += "✅ Работает нормально\n"
        else:
            status_msg += "⚠️ Возвращает пустые данные\n"
    except asyncio.TimeoutError:
        status_msg += "⏱️ Превышено время ожидания (>10s)\n"
    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            status_msg += "🚫 **Лимит исчерпан (429)**\n"
            status_msg += "💡 Проверь: https://aistudio.google.com/app/apikey\n"
        elif "401" in error_str or "UNAUTHENTICATED" in error_str:
            status_msg += "🔐 Ошибка авторизации (неверный API ключ)\n"
        elif "403" in error_str or "PERMISSION_DENIED" in error_str:
            status_msg += "🚫 Доступ запрещен (проверь настройки API)\n"
        else:
            status_msg += f"❌ Ошибка: {error_str[:100]}\n"
    
    status_msg += "\n"
    
    # Test Ollama
    status_msg += "**🟣 Ollama (локальный):**\n"
    try:
        ollama = OllamaProvider()
        # Check if Ollama is available
        is_available = await asyncio.wait_for(
            ollama.is_available(),
            timeout=5
        )
        if is_available:
            # Try a test estimation
            test_result = await asyncio.wait_for(
                ollama.estimate_food("яблоко"),
                timeout=15
            )
            if test_result and test_result.total_calories > 0:
                status_msg += "✅ Работает нормально\n"
            else:
                status_msg += "⚠️ Возвращает пустые данные\n"
        else:
            status_msg += "🔌 Не запущен (ollama serve)\n"
    except asyncio.TimeoutError:
        status_msg += "⏱️ Превышено время ожидания (>15s)\n"
    except Exception as e:
        error_str = str(e)
        if "Connection" in error_str or "connect" in error_str:
            status_msg += "🔌 Не запущен (ollama serve)\n"
        else:
            status_msg += f"❌ Ошибка: {error_str[:100]}\n"
    
    status_msg += "\n"
    status_msg += "💡 **Переключение провайдера:**\n"
    status_msg += "Измени `DEFAULT_AI_PROVIDER` в `.env`:\n"
    status_msg += "• `gemini` - Google Gemini (облако)\n"
    status_msg += "• `ollama` - Ollama (локально)\n"
    
    await message.answer(status_msg, parse_mode="Markdown")
