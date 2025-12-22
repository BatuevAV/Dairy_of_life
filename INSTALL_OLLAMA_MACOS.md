# Установка Ollama на macOS

## ⚠️ Важно: скрипт install.sh только для Linux!

Скрипт `https://ollama.com/install.sh` **не работает на macOS** - он проверяет `uname -s` и выдаст ошибку:
```
ERROR: This script is intended to run on Linux only.
```

## Варианты установки на macOS

### Вариант 1: Через Homebrew (рекомендуется)

Если у вас установлен Homebrew:

```bash
brew install ollama
```

### Вариант 2: Скачать .app напрямую (без Homebrew)

1. Скачайте Ollama.app с официального сайта:
   ```bash
   curl -L https://ollama.com/download/Ollama-darwin.zip -o Ollama.zip
   ```

2. Распакуйте:
   ```bash
   unzip Ollama.zip
   ```

3. Переместите в Applications:
   ```bash
   mv Ollama.app /Applications/
   ```

4. Запустите приложение:
   ```bash
   open /Applications/Ollama.app
   ```

5. Ollama создаст CLI в `/usr/local/bin/ollama` автоматически

### Вариант 3: Установка Homebrew, затем Ollama

Если у вас нет Homebrew, установите его:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Затем:

```bash
brew install ollama
```

## Проверка установки

После установки проверьте:

```bash
which ollama
ollama --version
```

## Запуск Ollama

### GUI приложение (Вариант 2)

Просто откройте Ollama.app из Applications - оно запустится в фоне и добавит иконку в menu bar.

### CLI сервер

```bash
ollama serve
```

Оставьте это окно терминала открытым!

## Скачивание модели

```bash
ollama pull llama3.2
```

## Тестирование

```bash
ollama run llama3.2 "Оцени калории в сэндвиче"
```

## Что делать дальше?

1. Выберите подходящий вариант установки
2. Скачайте модель `llama3.2`
3. Запустите `ollama serve` (или откройте Ollama.app)
4. Примените миграции БД (файл `migrate_db.sql`)
5. Перезапустите бота

---

**Рекомендую Вариант 2** (скачать .app) - не требует Homebrew и работает сразу.
