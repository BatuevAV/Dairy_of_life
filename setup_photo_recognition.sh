#!/bin/bash
# Быстрая настройка распознавания фото

echo "🚀 Настройка распознавания еды по фото"
echo "======================================"
echo ""

# Проверка виртуального окружения
if [ ! -d "venv" ]; then
    echo "❌ Виртуальное окружение не найдено"
    echo "   Сначала запустите: python -m venv venv"
    exit 1
fi

# Активация venv
echo "✅ Активирую виртуальное окружение..."
source venv/bin/activate

# Проверка .env
if [ ! -f ".env" ]; then
    echo "❌ Файл .env не найден"
    echo "   Скопируйте: cp .env.example .env"
    exit 1
fi

# Проверка GEMINI_API_KEY
if ! grep -q "GEMINI_API_KEY=" .env; then
    echo ""
    echo "⚠️  GEMINI_API_KEY не найден в .env"
    echo ""
    echo "📝 Получите бесплатный API ключ:"
    echo "   1. Откройте: https://makersuite.google.com/app/apikey"
    echo "   2. Войдите через Google аккаунт"
    echo "   3. Нажмите 'Create API Key'"
    echo "   4. Скопируйте ключ"
    echo ""
    read -p "Введите ваш Gemini API ключ: " api_key
    echo "GEMINI_API_KEY=$api_key" >> .env
    echo "✅ API ключ добавлен в .env"
else
    echo "✅ GEMINI_API_KEY найден в .env"
fi

# Применение миграций
echo ""
echo "🔄 Применяю миграции БД..."
python apply_photo_migrations.py

if [ $? -ne 0 ]; then
    echo "❌ Ошибка при применении миграций"
    exit 1
fi

# Тестирование
echo ""
echo "🧪 Проверяю Gemini API..."
python test_photo_recognition.py

echo ""
echo "======================================"
echo "✅ НАСТРОЙКА ЗАВЕРШЕНА!"
echo ""
echo "📝 Следующие шаги:"
echo "   1. python -m bot.main       # Запустить бота"
echo "   2. Отправить фото еды боту  # Протестировать"
echo ""
echo "📖 Документация:"
echo "   - PHOTO_READY.md            # Быстрый старт"
echo "   - PHOTO_RECOGNITION.md      # Полная документация"
echo ""
echo "======================================"
