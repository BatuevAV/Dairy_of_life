# 📸 Распознавание еды по фото

## Быстрый старт

### 1. Получите бесплатный API ключ Google Gemini

1. Перейдите на https://makersuite.google.com/app/apikey
2. Войдите через Google аккаунт
3. Нажмите **Create API Key**
4. Скопируйте ключ

**Бесплатный лимит:** 15 запросов/минуту, 1500/день

### 2. Добавьте ключ в .env

```bash
# Откройте .env файл
nano .env

# Добавьте строку:
GEMINI_API_KEY=ваш_ключ_здесь
```

### 3. Примените миграции БД

```bash
source venv/bin/activate
python apply_photo_migrations.py
```

### 4. Запустите бота

```bash
python -m bot.main
# или с мониторингом:
python monitor_logs.py
```

## Как использовать

### Просто отправьте фото еды боту!

Бот автоматически:
1. ✅ Распознает что на фото
2. 🔢 Посчитает калории и БЖУ
3. ❓ Задаст уточняющие вопросы (1-3 штуки)
4. ✏️ Обновит оценку после ваших ответов
5. 💾 Попросит подтверждение перед записью

### Пример диалога

**Вы:** [отправляете фото пасты]

**Бот:**
```
📸 Я вижу на фото:
• паста с курицей
• соус (похоже сливочный)

паста карбонара с курицей, примерно 1 порция

Оценка калорий: ~820 ккал
БЖУ: 40/30/85г
Уверенность: 🟢 medium (75%)

Я предположил:
• Порция стандартная (~300г)
• Соус сливочный
• Без дополнительного сыра

Уточните пожалуйста:

Соус какой?
```
[Кнопки: сливочный | томатный | без соуса]

**Вы:** [нажимаете "сливочный"]

**Бот:**
```
Отлично! соус: сливочный

Следующий вопрос (2/3):
Добавляли масло/сыр сверху?
```
[Кнопки: нет | немного | да]

**Вы:** [нажимаете "немного"]

**Бот:**
```
🔄 Обновляю оценку с учетом ваших ответов...

Финальная оценка:

📊 Калории: ~880 ккал
БЖУ: 42/35/86г

Ваши уточнения:
• sauce: сливочный
• extra: немного
```
[Кнопки: ✅ Записать | ✏️ Изменить | ❌ Отменить]

**Вы:** [нажимаете ✅ Записать]

**Бот:**
```
✅ Записано!

📸 паста с курицей, соус (похоже сливочный)

Калории: +880 ккал
БЖУ: +42/35/86г

📊 Посмотреть сводку: /today
```

## Приватность

### ⚠️ Внимание

При отправке фото:
- Изображение отправляется на серверы **Google Gemini** для анализа
- Google может использовать данные согласно их [политике](https://ai.google.dev/gemini-api/terms)

### 🔒 Что хранится в БД

По умолчанию бот **НЕ сохраняет фото**. Хранится только:
- ✅ Дата записи
- ✅ Итоговые калории и БЖУ
- ✅ Текстовое описание ("паста с курицей, соус сливочный")
- ✅ Ваши ответы на вопросы
- ✅ Уровень уверенности AI

Фото используется только для анализа, затем удаляется.

### 📁 Настройка сохранения фото (будущая функция)

```
/settings → Сохранять фото: Вкл/Выкл
```

По умолчанию: **Выкл** (максимальная приватность)

## Технические детали

### Архитектура

```
bot/ai/
  vision_base.py              # Абстрактный VisionAIProvider
  gemini_vision_provider.py   # Реализация для Gemini Vision

bot/handlers/
  photo_input.py              # Обработчик фото с вопросами
```

### Модель данных

```python
# User
save_photos: bool = False  # Настройка сохранения

# DayEntry
photo_analyzed: bool              # Было ли фото
photo_file_id: str                # Telegram file_id (если save_photos=True)
photo_description: str            # Что видит AI
photo_clarifications_json: str    # JSON с вопросами/ответами
food_description: str             # Итоговое описание еды
```

### Расширение

Легко добавить другие провайдеры:

```python
# bot/ai/openai_vision_provider.py
class OpenAIVisionProvider(VisionAIProvider):
    async def analyze_food_photo(...):
        # GPT-4 Vision implementation
        ...

# bot/ai/claude_vision_provider.py  
class ClaudeVisionProvider(VisionAIProvider):
    async def analyze_food_photo(...):
        # Claude 3 Vision implementation
        ...
```

## Отладка

### Проверить доступность Gemini API

```bash
python -c "
import asyncio
from bot.ai.gemini_vision_provider import GeminiVisionProvider
import os

async def test():
    api_key = os.getenv('GEMINI_API_KEY')
    provider = GeminiVisionProvider(api_key=api_key)
    available = await provider.is_available()
    print(f'Gemini доступен: {available}')
    
asyncio.run(test())
"
```

### Проверить колонки БД

```bash
python check_db.py
```

Должны быть:
- `users.save_photos`
- `day_entries.photo_analyzed`
- `day_entries.photo_file_id`
- `day_entries.photo_description`
- `day_entries.photo_clarifications_json`
- `day_entries.food_description`

## Лимиты

### Gemini Free Tier

- **RPM:** 15 запросов/минуту
- **RPD:** 1500 запросов/день
- **Размер фото:** до 4MB

### Бот лимиты

- **AI запросы:** 30/день (настройка `ai_requests_limit`)
- Распознавание фото считается за 1 AI запрос
- Лимит сбрасывается в 00:00 Asia/Bangkok

## Roadmap

- [ ] Переспрос AI с учетом уточнений (сейчас просто показывает финальную оценку)
- [ ] Кэширование распознавания для популярных блюд (Starbucks, McDonalds)
- [ ] Локальный анализ через YOLO + базу продуктов (без отправки в облако)
- [ ] Опция выбора провайдера (Gemini / OpenAI / Claude)
- [ ] Сохранение фото в S3/MinIO (опционально)
- [ ] История фото в /export
