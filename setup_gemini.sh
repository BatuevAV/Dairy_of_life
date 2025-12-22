#!/bin/bash
# Быстрая настройка Gemini API ключа

echo "🔧 Настройка Gemini Vision API"
echo "======================================"
echo ""

# Проверка .env
if [ ! -f ".env" ]; then
    echo "⚠️  Файл .env не найден, создаю из .env.example..."
    cp .env.example .env
    echo "✅ Файл .env создан"
fi

# Проверка текущего ключа
if grep -q "^GEMINI_API_KEY=" .env && ! grep -q "^GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE" .env; then
    echo "✅ GEMINI_API_KEY уже настроен в .env"
    echo ""
    echo "🧪 Проверяю работоспособность..."
    source venv/bin/activate 2>/dev/null
    python diagnose_gemini.py
    exit 0
fi

echo "📝 Нужно получить Gemini API ключ"
echo ""
echo "Шаги:"
echo "  1. Откройте в браузере: https://aistudio.google.com/app/apikey"
echo "  2. Войдите через Google аккаунт"
echo "  3. Нажмите 'Create API key'"
echo "  4. Скопируйте ключ (начинается с AIza...)"
echo ""

read -p "Вставьте ваш Gemini API ключ: " api_key

if [ -z "$api_key" ]; then
    echo "❌ Ключ не введен"
    exit 1
fi

# Проверка формата
if [[ ! $api_key =~ ^AIza ]]; then
    echo "⚠️  Предупреждение: Обычно ключ начинается с 'AIza'"
    read -p "Продолжить? (y/n): " confirm
    if [ "$confirm" != "y" ]; then
        exit 1
    fi
fi

# Добавление в .env
if grep -q "^GEMINI_API_KEY=" .env; then
    # Обновить существующую строку
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s|^GEMINI_API_KEY=.*|GEMINI_API_KEY=$api_key|" .env
    else
        # Linux
        sed -i "s|^GEMINI_API_KEY=.*|GEMINI_API_KEY=$api_key|" .env
    fi
    echo "✅ GEMINI_API_KEY обновлен в .env"
else
    # Добавить новую строку
    echo "" >> .env
    echo "# Gemini Vision API" >> .env
    echo "GEMINI_API_KEY=$api_key" >> .env
    echo "✅ GEMINI_API_KEY добавлен в .env"
fi

# Проверка
echo ""
echo "🧪 Проверяю работоспособность API..."
echo ""

source venv/bin/activate 2>/dev/null
python diagnose_gemini.py

echo ""
echo "======================================"
echo "✅ Настройка завершена!"
echo ""
echo "📝 Следующие шаги:"
echo "   1. python -m bot.main       # Запустить бота"
echo "   2. Отправить фото еды боту  # Протестировать"
echo ""
echo "======================================"
