# Установка и настройка Ollama для AI-оценки калорий

## Шаг 1: Установка Ollama

### macOS

```bash
# Установка через Homebrew
brew install ollama

# Или скачать с официального сайта
# https://ollama.ai
```

### Linux

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

## Шаг 2: Скачивание модели

Рекомендуемые модели (от меньшей к большей):

```bash
# Легкая модель (быстрая, 2GB)
ollama pull llama3.2

# Средняя модель (точнее, 4.7GB)
ollama pull llama3.2:8b

# Тяжелая модель (самая точная, 7.4GB)
ollama pull llama3.1
```

**Для начала рекомендую `llama3.2`** - она быстрая и достаточно точная.

## Шаг 3: Запуск Ollama

```bash
# Запустить сервер Ollama
ollama serve
```

Ollama запустится на `http://localhost:11434`

Оставьте это окно терминала открытым!

## Шаг 4: Проверка работы

Откройте новое окно терминала и проверьте:

```bash
# Проверить, что Ollama работает
curl http://localhost:11434/api/tags

# Протестировать модель
ollama run llama3.2 "Оцени калории в сэндвиче с ветчиной и сыром"
```

## Шаг 5: Автозапуск (опционально)

### macOS - launchd

Создайте файл `~/Library/LaunchAgents/com.ollama.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ollama</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/ollama</string>
        <string>serve</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/ollama.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/ollama.error.log</string>
</dict>
</plist>
```

Загрузите:

```bash
launchctl load ~/Library/LaunchAgents/com.ollama.plist
```

### Linux - systemd

Ollama автоматически создаст systemd service при установке:

```bash
sudo systemctl enable ollama
sudo systemctl start ollama
sudo systemctl status ollama
```

## Настройка модели в боте

По умолчанию бот использует модель `llama3.2` на `localhost:11434`.

Если хотите использовать другую модель, измените в файле:
`bot/handlers/free_input.py`, строка ~70:

```python
ai_provider = OllamaProvider(
    host="http://localhost:11434",
    model="llama3.2"  # Измените на нужную модель
)
```

## Проверка работы AI в боте

После запуска бота отправьте ему:

```
Еда: Сэндвич из Starbucks Multigrain ham and three cheese, macaron, чай без сахара
```

Бот должен ответить:

```
🤖 Оцениваю калорийность с помощью AI...

📝 Распознал следующие данные:

🍽 Еда:
🤖 Оценка AI (llama3.2):
  • Multigrain ham and three cheese sandwich: 450 ккал
    Б: 25г, Ж: 15г, У: 45г
  • Macaron: 140 ккал
    Б: 2г, Ж: 6г, У: 20г
  • Чай без сахара: 0 ккал
    Б: 0г, Ж: 0г, У: 0г

  Итого: 590 ккал
  БЖУ: 27/21/65
  📊 Точность оценки: ~75%

✅ Подтвердить | ❌ Отменить
```

## Лимиты AI

- По умолчанию: **30 запросов в день** на пользователя
- Лимит сбрасывается в полночь (по вашему timezone)
- Владелец может изменить лимит в БД через `/settings`

## Устранение проблем

### Ollama не запускается

```bash
# Проверить логи
tail -f /tmp/ollama.log

# Убить зависшие процессы
pkill ollama
ollama serve
```

### Модель не найдена

```bash
# Проверить список моделей
ollama list

# Скачать нужную модель
ollama pull llama3.2
```

### Бот говорит "AI-сервис недоступен"

1. Проверьте, что Ollama запущен: `curl http://localhost:11434/api/tags`
2. Проверьте логи бота
3. Проверьте, что модель скачана: `ollama list`

## Требования к ресурсам

- **Процессор**: M1/M2 Mac или любой современный CPU (2+ ядра)
- **RAM**: 8GB (рекомендуется 16GB)
- **Диск**: 2-8GB в зависимости от модели
- **Скорость**: 
  - На M1 Mac: ~2-3 секунды на запрос
  - На Intel Mac: ~5-10 секунд
  - На Linux server: ~3-7 секунд

---

**Готово! Теперь бот будет автоматически оценивать калории с помощью AI.** 🤖
