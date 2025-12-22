"""
Быстрая проверка основных функций бота
"""
import asyncio
import sys
from pathlib import Path
from datetime import time

sys.path.insert(0, str(Path(__file__).parent))

# Цвета для вывода
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'
BOLD = '\033[1m'

def test(name: str):
    """Декоратор для тестов"""
    def decorator(func):
        func.__test_name__ = name
        return func
    return decorator

async def run_tests():
    """Запуск всех тестов"""
    passed = 0
    failed = 0
    tests_list = []
    
    # ===== Тесты парсера =====
    @test("Парсинг сна")
    def test_parse_sleep():
        from bot.parsers.free_text_parser import FreeTextParser
        parser = FreeTextParser()
        parsed, missing = parser.parse("Сон: 22:30-04:00")
        assert 'sleep' in parsed, "Sleep не распознан"
        assert parsed['sleep'] is not None, "Sleep данные пусты"
    
    @test("Парсинг тренировки")
    def test_parse_workout():
        from bot.parsers.free_text_parser import FreeTextParser
        parser = FreeTextParser()
        parsed, missing = parser.parse("Тренировка: зал 60 мин")
        assert 'workout' in parsed, "Workout не распознан"
        assert parsed['workout'] is not None, "Workout данные пусты"
    
    @test("Парсинг еды с калориями")
    def test_parse_food():
        from bot.parsers.free_text_parser import FreeTextParser
        parser = FreeTextParser()
        parsed, missing = parser.parse("Еда: Сэндвич 450 ккал")
        assert 'food' in parsed, "Food не распознана"
        assert parsed['food'] is not None, "Food данные пусты"
    
    # ===== Тесты расчетов =====
    @test("Расчет BMR")
    def test_bmr():
        from bot.calculations.calories import calculate_bmr
        bmr = calculate_bmr(weight=70, height=179, age=28, gender="male")
        assert bmr > 1600 and bmr < 1700, f"BMR вне ожидаемого диапазона: {bmr}"
    
    @test("Расчет калорий от шагов")
    def test_steps():
        from bot.calculations.calories import calculate_steps_kcal
        kcal = calculate_steps_kcal(steps=10000, step_coef=0.026)
        assert kcal == 260.0, f"Неправильный расчет шагов: {kcal}"
    
    @test("Расчет общих калорий")
    def test_total_burned():
        from bot.calculations.calories import calculate_total_burned
        total = calculate_total_burned(bmr=1683.75, kcal_steps=260, kcal_workout=375)
        expected = 1683.75 + 260 + 375
        assert abs(total - expected) < 0.1, f"Неправильный расчет: {total} != {expected}"
    
    # ===== Тесты AI =====
    @test("Проверка доступности Ollama")
    async def test_ollama_available():
        from bot.ai.ollama_provider import OllamaProvider
        provider = OllamaProvider()
        is_available = await provider.is_available()
        assert is_available, "Ollama не доступен"
    
    @test("Получение имени провайдера")
    def test_provider_name():
        from bot.ai.ollama_provider import OllamaProvider
        provider = OllamaProvider()
        name = provider.get_provider_name()
        assert "Ollama" in name and "llama3.2" in name, f"Неправильное имя: {name}"
    
    # Собираем все тесты
    import inspect
    current_frame = inspect.currentframe()
    local_vars = current_frame.f_locals
    
    for name, obj in local_vars.items():
        if callable(obj) and hasattr(obj, '__test_name__'):
            tests_list.append(obj)
    
    # Запускаем тесты
    print(f"\n{BOLD}🧪 Быстрая проверка бота{RESET}\n")
    print(f"{'='*60}\n")
    
    for test_func in tests_list:
        test_name = test_func.__test_name__
        try:
            if asyncio.iscoroutinefunction(test_func):
                await test_func()
            else:
                test_func()
            print(f"{GREEN}✅ {test_name}{RESET}")
            passed += 1
        except AssertionError as e:
            print(f"{RED}❌ {test_name}: {e}{RESET}")
            failed += 1
        except Exception as e:
            print(f"{YELLOW}⚠️  {test_name}: {type(e).__name__}: {e}{RESET}")
            failed += 1
    
    # Итоги
    print(f"\n{'='*60}\n")
    print(f"{BOLD}📊 Результаты:{RESET}")
    print(f"  {GREEN}Пройдено: {passed}{RESET}")
    print(f"  {RED}Провалено: {failed}{RESET}")
    print(f"  {BOLD}Всего: {passed + failed}{RESET}\n")
    
    if failed == 0:
        print(f"{GREEN}{BOLD}🎉 Все тесты пройдены!{RESET}\n")
        return 0
    else:
        print(f"{RED}{BOLD}❌ Есть проваленные тесты{RESET}\n")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(run_tests())
    sys.exit(exit_code)
