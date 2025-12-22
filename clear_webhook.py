"""
Скрипт для отмены webhook и очистки pending updates
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from aiogram import Bot
from bot.config import settings

async def clear_webhook():
    bot = Bot(token=settings.BOT_TOKEN)
    
    try:
        # Удаляем webhook (если он был установлен)
        webhook_info = await bot.get_webhook_info()
        if webhook_info.url:
            print(f"📡 Найден webhook: {webhook_info.url}")
            await bot.delete_webhook(drop_pending_updates=True)
            print("✅ Webhook удален")
        else:
            print("ℹ️  Webhook не установлен")
        
        # Очищаем pending updates
        print("🧹 Очищаю pending updates...")
        await bot.delete_webhook(drop_pending_updates=True)
        print("✅ Pending updates очищены")
        
        # Проверяем бота
        me = await bot.get_me()
        print(f"\n✅ Бот готов: @{me.username} (ID: {me.id})")
        print("\n💡 Теперь можно запустить бота: python -m bot.main")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    print("🔧 Очистка webhook и pending updates...\n")
    asyncio.run(clear_webhook())
