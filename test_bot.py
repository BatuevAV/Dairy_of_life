"""
Быстрый тест запуска бота
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def test_bot():
    print("🔍 Проверяю импорты...")
    
    try:
        from bot import config
        print("✅ Config импортирован")
    except Exception as e:
        print(f"❌ Ошибка в config: {e}")
        return False
    
    try:
        from bot.database import db
        print("✅ Database импортирован")
    except Exception as e:
        print(f"❌ Ошибка в database: {e}")
        return False
    
    try:
        from bot.handlers import start, mode, free_input, guided_input, reports, export, settings, admin
        print("✅ Все handlers импортированы")
    except Exception as e:
        print(f"❌ Ошибка в handlers: {e}")
        return False
    
    try:
        from bot.ai.ollama_provider import OllamaProvider
        print("✅ OllamaProvider импортирован")
        
        # Проверим доступность Ollama
        provider = OllamaProvider()
        is_available = await provider.is_available()
        print(f"{'✅' if is_available else '❌'} Ollama сервер {'доступен' if is_available else 'недоступен'} на {provider.host}")
        
    except Exception as e:
        print(f"❌ Ошибка в OllamaProvider: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    try:
        from aiogram import Bot, Dispatcher
        from bot.config import settings
        
        bot = Bot(token=settings.BOT_TOKEN)
        print("✅ Bot создан успешно")
        
        # Проверим токен
        me = await bot.get_me()
        print(f"✅ Бот подключен: @{me.username} (ID: {me.id})")
        
        await bot.session.close()
        
    except Exception as e:
        print(f"❌ Ошибка при создании бота: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n✅ Все проверки пройдены! Бот готов к запуску.")
    return True

if __name__ == "__main__":
    print("🚀 Быстрая проверка бота перед запуском...\n")
    result = asyncio.run(test_bot())
    sys.exit(0 if result else 1)
