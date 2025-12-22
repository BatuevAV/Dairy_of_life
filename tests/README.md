# 🧪 Тесты для Telegram Bot - Diary of Food

## Структура тестов

```
tests/
├── conftest.py              # Pytest fixtures и конфигурация
├── test_parsers.py          # Тесты парсеров свободного ввода
├── test_calculations.py     # Тесты расчета калорий
└── test_ai_provider.py      # Тесты AI провайдера (Ollama)
```

## Установка зависимостей

```bash
source venv/bin/activate
pip install pytest pytest-asyncio pytest-cov aiosqlite
```

## Запуск тестов

### Все тесты

```bash
pytest
```

### С подробным выводом

```bash
pytest -v
```

### С покрытием кода

```bash
pytest --cov=bot --cov-report=html
```

После этого откройте `htmlcov/index.html` для просмотра покрытия.

### Конкретный файл

```bash
pytest tests/test_parsers.py
```

### Конкретный тест

```bash
pytest tests/test_parsers.py::TestFreeTextParser::test_parse_sleep
```

## Покрытие

### Что покрыто тестами:

✅ **Парсеры (test_parsers.py)**
- Парсинг сна (русский/английский)
- Парсинг тренировок (зал, плавание, бег, велосипед)
- Парсинг шагов, веса, талии
- Парсинг еды с калориями и без (для AI)
- Парсинг сложных записей

✅ **Расчеты (test_calculations.py)**
- Расчет времени сна (через полночь, несколько периодов)
- Расчет BMR (мужчины/женщины)
- Расчет калорий от шагов
- Расчет калорий от тренировок
- Расчет общих потраченных калорий
- Расчет баланса

✅ **AI Provider (test_ai_provider.py)**
- Генерация промптов
- Парсинг JSON ответов от AI
- Обработка ошибок
- Проверка доступности Ollama
- Расчет итоговых значений

## Мониторинг логов

### Запуск бота с цветными логами

```bash
python monitor_logs.py
```

Этот скрипт:
- ✅ Запускает бота
- 🎨 Раскрашивает логи по уровням (ERROR - красный, WARNING - желтый)
- 🔍 Показывает только ERROR и WARNING
- 📊 Подсчитывает количество ошибок и предупреждений
- 🔥 Показывает последние 5 ошибок после остановки

### Остановка

Нажмите `Ctrl+C` для остановки бота и просмотра статистики.

## Непрерывная интеграция (CI)

### GitHub Actions

Создайте `.github/workflows/tests.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-asyncio pytest-cov
    
    - name: Run tests
      run: pytest --cov=bot --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

## Примеры

### Запуск тестов с цветным выводом

```bash
pytest --color=yes
```

### Запуск только быстрых тестов (без AI)

```bash
pytest -m "not slow"
```

### Запуск с остановкой на первой ошибке

```bash
pytest -x
```

### Запуск с отладочным выводом

```bash
pytest -s
```

## Добавление новых тестов

1. Создайте файл `test_*.py` в папке `tests/`
2. Импортируйте `pytest` и тестируемые модули
3. Создайте класс `Test*` с методами `test_*`
4. Используйте `assert` для проверок
5. Используйте `@pytest.mark.asyncio` для async тестов

Пример:

```python
import pytest

class TestMyFeature:
    def test_something(self):
        result = my_function()
        assert result == expected_value
    
    @pytest.mark.asyncio
    async def test_async_something(self):
        result = await my_async_function()
        assert result is not None
```

---

**Покрытие кода:** Стремимся к 80%+  
**Статус:** ✅ Тесты готовы к запуску
