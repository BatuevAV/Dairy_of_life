"""
Тест Gemini Vision API с детальной отладкой
"""
import asyncio
import aiohttp
import os
import sys
import json
import base64
from dotenv import load_dotenv

# Загружаем .env файл
load_dotenv()

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def test_gemini_endpoint():
    """Проверка правильности endpoint"""
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key:
        print("❌ GEMINI_API_KEY не найден в .env")
        return False
    
    print("🔍 Тест Gemini Vision API")
    print("=" * 60)
    print(f"API Key: {api_key[:15]}...")
    
    # Сначала получаем список доступных моделей
    print("\n📋 Получаю список доступных моделей...")
    try:
        async with aiohttp.ClientSession() as session:
            list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
            async with session.get(list_url) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'models' in data:
                        print(f"✅ Найдено {len(data['models'])} моделей:")
                        vision_models = []
                        for model in data['models']:
                            name = model.get('name', '')
                            # Ищем модели с поддержкой изображений
                            supported_methods = model.get('supportedGenerationMethods', [])
                            if 'generateContent' in supported_methods:
                                model_id = name.split('/')[-1] if '/' in name else name
                                print(f"   • {model_id}")
                                if any(x in model_id.lower() for x in ['vision', 'pro', 'flash']):
                                    vision_models.append(model_id)
                        
                        if vision_models:
                            print(f"\n✅ Модели с Vision: {', '.join(vision_models[:3])}")
                            # Тестируем первую найденную модель
                            return vision_models[0]
                elif response.status == 403:
                    print(f"❌ 403 - Доступ запрещен. API ключ не активирован или неправильный")
                    print(f"   Проверьте: https://aistudio.google.com/app/apikey")
                else:
                    text = await response.text()
                    print(f"❌ {response.status} - {text[:100]}")
    except Exception as e:
        print(f"❌ Ошибка при получении списка моделей: {e}")
    
    # Если не удалось получить список, пробуем стандартные модели
    print("\n🧪 Тестирую стандартные модели...")
    
    # Тестируем разные модели
    models = [
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash",
        "gemini-1.5-pro-latest",
        "gemini-1.5-pro",
        "gemini-pro-vision",
        "gemini-pro",
        "models/gemini-1.5-flash-latest",
        "models/gemini-1.5-flash",
        "models/gemini-pro-vision"
    ]
    
    for model in models:
        print(f"\n🧪 Тестирую модель: {model}")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        
        # Простой текстовый запрос для проверки модели
        payload = {
            "contents": [{
                "parts": [{
                    "text": "Hello! Just checking if this model works."
                }]
            }]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers={"Content-Type": "application/json"}) as response:
                    status = response.status
                    text = await response.text()
                    
                    if status == 200:
                        print(f"   ✅ Модель работает!")
                        data = json.loads(text)
                        if 'candidates' in data:
                            print(f"   ✅ Формат ответа правильный")
                            return model  # Возвращаем первую рабочую модель
                    elif status == 404:
                        print(f"   ❌ 404 - Модель не найдена")
                    elif status == 400:
                        print(f"   ⚠️  400 - Неправильный запрос: {text[:100]}")
                    elif status == 403:
                        print(f"   ❌ 403 - Доступ запрещен (проверьте API ключ)")
                    else:
                        print(f"   ❌ {status} - {text[:100]}")
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
    
    return None


async def test_vision_with_dummy_image(working_model):
    """Тест с минимальным изображением"""
    api_key = os.getenv('GEMINI_API_KEY')
    
    print("\n" + "=" * 60)
    print("📸 Тест Vision с изображением")
    print("=" * 60)
    
    # Создаем минимальное 1x1 пиксель JPEG изображение (base64)
    # Это валидный JPEG header + минимальные данные
    dummy_jpeg = "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAIBAQIBAQICAgICAgICAwUDAwMDAwYEBAMFBwYHBwcGBwcICQsJCAgKCAcHCg0KCgsMDAwMBwkODw0MDgsMDAz/2wBDAQICAgMDAwYDAwYMCAcIDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAz/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCwAA8A/9k="
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{working_model}:generateContent?key={api_key}"
    
    payload = {
        "contents": [{
            "parts": [
                {"text": "What do you see in this image?"},
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": dummy_jpeg
                    }
                }
            ]
        }],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 100
        }
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers={"Content-Type": "application/json"}) as response:
                status = response.status
                text = await response.text()
                
                if status == 200:
                    print("✅ Vision API работает!")
                    data = json.loads(text)
                    if 'candidates' in data:
                        response_text = data['candidates'][0]['content']['parts'][0]['text']
                        print(f"✅ Ответ: {response_text[:100]}")
                        return True
                else:
                    print(f"❌ Ошибка {status}: {text[:200]}")
                    return False
    except Exception as e:
        print(f"❌ Исключение: {e}")
        return False


async def main():
    print("🚀 Диагностика Gemini Vision API")
    print("=" * 60 + "\n")
    
    # Шаг 1: Найти рабочую модель
    working_model = await test_gemini_endpoint()
    
    if not working_model:
        print("\n❌ Ни одна модель не работает!")
        print("\n📝 Возможные причины:")
        print("   1. Неправильный API ключ")
        print("   2. API ключ не активирован")
        print("   3. Нужно принять Terms of Service: https://makersuite.google.com")
        print("   4. Регион не поддерживается")
        return
    
    print(f"\n✅ Найдена рабочая модель: {working_model}")
    
    # Шаг 2: Тест Vision API
    vision_works = await test_vision_with_dummy_image(working_model)
    
    # Итог
    print("\n" + "=" * 60)
    if vision_works:
        print("✅ ВСЕ РАБОТАЕТ!")
        print(f"\n📝 Используйте модель: {working_model}")
        print("\nОбновите код:")
        print(f'   model: str = "{working_model}"')
    else:
        print("❌ Vision API не работает")
        print("\n📝 Проверьте:")
        print("   1. API ключ имеет доступ к Vision API")
        print("   2. Включен Gemini API в Google Cloud Console")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
