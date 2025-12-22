# Инструкция по запуску бота

## Требования

- Python 3.11 или выше
- PostgreSQL 12 или выше
- Telegram Bot Token (получить у [@BotFather](https://t.me/BotFather))
- Ваш Telegram User ID (узнать у [@userinfobot](https://t.me/userinfobot))

## Шаг 1: Клонирование и подготовка

```bash
cd /Users/aleksandrbatuev/Documents/Dairy_of_life
```

Проект уже готов к работе!

## Шаг 2: Создание виртуального окружения

### macOS/Linux:

```bash
# Создать виртуальное окружение
python3 -m venv venv

# Активировать
source venv/bin/activate
```

### Windows:

```bash
# Создать виртуальное окружение
python -m venv venv

# Активировать
venv\Scripts\activate
```

## Шаг 3: Установка зависимостей

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## Шаг 4: Настройка PostgreSQL

### Установка PostgreSQL (если ещё не установлен)

**macOS (Homebrew):**
```bash
brew install postgresql@16
brew services start postgresql@16
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**Windows:**
Скачать с [официального сайта](https://www.postgresql.org/download/windows/)

### Создание базы данных

```bash
# Подключиться к PostgreSQL
psql -U postgres

# В консоли PostgreSQL:
CREATE DATABASE dairy_of_life;
CREATE USER dairy_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE dairy_of_life TO dairy_user;
\q
```

## Шаг 5: Конфигурация бота

Создайте файл `.env` в корне проекта:

```bash
cp .env.example .env
```

Отредактируйте `.env`:

```env
# Telegram Bot Token (получить у @BotFather)
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Ваш Telegram User ID (узнать у @userinfobot)
OWNER_TELEGRAM_ID=123456789

# PostgreSQL настройки
DB_HOST=localhost
DB_PORT=5432
DB_USER=dairy_user
DB_PASSWORD=your_secure_password
DB_NAME=dairy_of_life

# Часовой пояс (Asia/Bangkok по умолчанию)
TIMEZONE=Asia/Bangkok

# Режим отладки (True/False)
DEBUG=False
```

## Шаг 6: Получение токена бота

1. Откройте Telegram
2. Найдите [@BotFather](https://t.me/BotFather)
3. Отправьте команду `/newbot`
4. Следуйте инструкциям:
   - Введите имя бота (например: "My Dairy Bot")
   - Введите username бота (должен заканчиваться на `bot`, например: `my_dairy_bot`)
5. Скопируйте токен и вставьте в `.env` как `BOT_TOKEN`

## Шаг 7: Получение вашего Telegram ID

1. Найдите [@userinfobot](https://t.me/userinfobot)
2. Отправьте любое сообщение
3. Скопируйте ваш ID и вставьте в `.env` как `OWNER_TELEGRAM_ID`

## Шаг 8: Запуск бота

### Убедитесь, что виртуальное окружение активировано:

```bash
# Должно быть активно (venv)
source venv/bin/activate  # macOS/Linux
# или
venv\Scripts\activate     # Windows
```

### Запустите бота:

```bash
python -m bot.main
```

Или:

```bash
python bot/main.py
```

Вы должны увидеть:

```
INFO - Starting bot...
INFO - Database initialized
INFO - Handlers registered
INFO - Bot started successfully!
INFO - Owner Telegram ID: 123456789
```

## Шаг 9: Проверка работы

1. Откройте Telegram
2. Найдите вашего бота по username
3. Отправьте `/start`
4. Бот должен ответить приветственным сообщением

## Остановка бота

Нажмите `Ctrl + C` в терминале.

## Автозапуск бота (опционально)

### macOS/Linux - Systemd Service

Создайте файл `/etc/systemd/system/dairy_bot.service`:

```ini
[Unit]
Description=Dairy of Life Telegram Bot
After=network.target postgresql.service

[Service]
Type=simple
User=your_username
WorkingDirectory=/Users/aleksandrbatuev/Documents/Dairy_of_life
Environment=PATH=/Users/aleksandrbatuev/Documents/Dairy_of_life/venv/bin
ExecStart=/Users/aleksandrbatuev/Documents/Dairy_of_life/venv/bin/python -m bot.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Включите и запустите:

```bash
sudo systemctl daemon-reload
sudo systemctl enable dairy_bot
sudo systemctl start dairy_bot
sudo systemctl status dairy_bot
```

### macOS - launchd

Создайте файл `~/Library/LaunchAgents/com.dairy.bot.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.dairy.bot</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/aleksandrbatuev/Documents/Dairy_of_life/venv/bin/python</string>
        <string>-m</string>
        <string>bot.main</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/aleksandrbatuev/Documents/Dairy_of_life</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/dairy_bot.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/dairy_bot.error.log</string>
</dict>
</plist>
```

Загрузите:

```bash
launchctl load ~/Library/LaunchAgents/com.dairy.bot.plist
```

## Устранение проблем

### Ошибка подключения к БД

Проверьте:
1. PostgreSQL запущен: `pg_isready`
2. База данных создана: `psql -U postgres -l | grep dairy_of_life`
3. Правильные данные в `.env`

### Бот не отвечает

Проверьте:
1. Токен бота правильный
2. Ваш Telegram ID правильный (бот работает только с owner)
3. Бот запущен и нет ошибок в логах

### Ошибки импорта

```bash
# Переустановите зависимости
pip install --upgrade -r requirements.txt
```

### Проблемы с виртуальным окружением

```bash
# Удалите и создайте заново
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Полезные команды

```bash
# Проверить статус PostgreSQL
pg_isready

# Подключиться к базе
psql -U dairy_user -d dairy_of_life

# Посмотреть таблицы
\dt

# Посмотреть записи пользователя
SELECT * FROM users;

# Посмотреть записи дневника
SELECT * FROM day_entries ORDER BY entry_date DESC LIMIT 10;
```

## Обновление бота

Если вы внесли изменения в код:

```bash
# Остановите бота (Ctrl+C)

# Активируйте виртуальное окружение
source venv/bin/activate

# Обновите зависимости (если нужно)
pip install -r requirements.txt

# Запустите снова
python -m bot.main
```

## Резервное копирование

### Бэкап базы данных:

```bash
pg_dump -U dairy_user dairy_of_life > backup_$(date +%Y%m%d).sql
```

### Восстановление:

```bash
psql -U dairy_user dairy_of_life < backup_20241222.sql
```

## Контакты и поддержка

При возникновении проблем проверьте:
1. Логи бота в консоли
2. Файл PROGRESS.md для истории изменений
3. README.md для документации

---

**Готово! Бот должен работать. Отправь /start в Telegram боту для начала работы! 🚀**
