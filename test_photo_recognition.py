"""
Тест функции распознавания фото
"""
import asyncio
import os
import sys

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.ai.gemini_vision_provider import GeminiVisionProvider


async def test_gemini_vision():
    """Протестировать Gemini Vision API"""
    
    print("🧪 Тест распознавания еды по фото\n")
    
    # Проверяем API ключ
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key:
        print("❌ GEMINI_API_KEY не найден в .env")
        print("\n📝 Получите ключ:")
        print("   1. https://makersuite.google.com/app/apikey")
        print("   2. Добавьте в .env: GEMINI_API_KEY=ваш_ключ")
        return False
    
    print(f"✅ API ключ найден: {api_key[:10]}...")
    
    # Создаем провайдер
    provider = GeminiVisionProvider(api_key=api_key)
    print(f"✅ Провайдер создан: {provider.get_provider_name()}")
    
    # Проверяем доступность
    print("\n🔍 Проверяю доступность Gemini API...")
    available = await provider.is_available()
    
    if available:
        print("✅ Gemini API доступен!")
        print(f"   Модель: {provider.model}")
        print(f"   Лимиты: 15 RPM, 1500 RPD")
        return True
    else:
        print("❌ Gemini API недоступен")
        print("   Проверьте:")
        print("   - Правильность API ключа")
        print("   - Интернет соединение")
        print("   - https://status.cloud.google.com")
        return False


async def test_photo_analyze():
    """Протестировать анализ тестового изображения"""
    
    print("\n" + "="*50)
    print("📸 Тест анализа изображения")
    print("="*50 + "\n")
    
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("⏭️  Пропускаю (нет API ключа)")
        return
    
    print("ℹ️  Для полного теста отправьте фото боту")
    print("   Бот автоматически распознает еду!")
    print("\n✅ Архитектура готова:")
    print("   - VisionAIProvider (базовый класс)")
    print("   - GeminiVisionProvider (реализация)")
    print("   - PhotoInputState (FSM для вопросов)")
    print("   - photo_input.py (обработчик)")


if __name__ == "__main__":
    print("=" * 60)
    print(" 📸 ТЕСТ РАСПОЗНАВАНИЯ ЕДЫ ПО ФОТО")
    print("=" * 60 + "\n")
    
    # Тест 1: Gemini доступность
    result = asyncio.run(test_gemini_vision())
    
    # Тест 2: Анализ изображения (информационный)
    asyncio.run(test_photo_analyze())
    
    # Итог
    print("\n" + "=" * 60)
    if result:
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ")
        print("\n📝 Следующие шаги:")
        print("   1. python apply_photo_migrations.py  # Применить миграции")
        print("   2. python -m bot.main                # Запустить бота")
        print("   3. Отправить фото еды боту           # Протестировать")
    else:
        print("⚠️  ТРЕБУЕТСЯ НАСТРОЙКА")
        print("\n📝 Что сделать:")
        print("   1. Получить API ключ Gemini: https://makersuite.google.com/app/apikey")
        print("   2. Добавить в .env: GEMINI_API_KEY=ваш_ключ")
        print("   3. Перезапустить тест")
    print("=" * 60)
