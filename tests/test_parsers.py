"""
Тесты для парсеров свободного ввода
"""
import pytest
from datetime import time
from bot.parsers.free_text_parser import FreeTextParser
from bot.database.models import WorkoutType


class TestFreeTextParser:
    """Тесты парсера свободного ввода"""
    
    @pytest.fixture
    def parser(self):
        return FreeTextParser()
    
    def test_parse_sleep(self, parser):
        """Тест парсинга сна"""
        text = "Сон: 22:30-04:00 и с 06:30-07:30"
        result = parser.parse(text)
        
        assert result['sleep'] is not None
        assert len(result['sleep']) == 2
        assert result['sleep'][0] == (time(22, 30), time(4, 0))
        assert result['sleep'][1] == (time(6, 30), time(7, 30))
    
    def test_parse_sleep_english(self, parser):
        """Тест парсинга сна на английском"""
        text = "Sleep: 23:00-07:00"
        result = parser.parse(text)
        
        assert result['sleep'] is not None
        assert len(result['sleep']) == 1
        assert result['sleep'][0] == (time(23, 0), time(7, 0))
    
    def test_parse_workout_gym(self, parser):
        """Тест парсинга тренировки в зале"""
        text = "Тренировка: зал 60 мин"
        result = parser.parse(text)
        
        assert result['workouts'] is not None
        assert len(result['workouts']) == 1
        assert result['workouts'][0]['type'] == WorkoutType.GYM
        assert result['workouts'][0]['minutes'] == 60
    
    def test_parse_workout_swimming(self, parser):
        """Тест парсинга плавания"""
        text = "Тренировка: плавание 45 минут"
        result = parser.parse(text)
        
        assert result['workouts'] is not None
        assert result['workouts'][0]['type'] == WorkoutType.SWIMMING
        assert result['workouts'][0]['minutes'] == 45
    
    def test_parse_steps(self, parser):
        """Тест парсинга шагов"""
        text = "Шаги: 12000"
        result = parser.parse(text)
        
        assert result['steps'] == 12000
    
    def test_parse_weight(self, parser):
        """Тест парсинга веса"""
        text = "Вес: 69.3 кг"
        result = parser.parse(text)
        
        assert result['weight'] == 69.3
    
    def test_parse_waist(self, parser):
        """Тест парсинга талии"""
        text = "Талия: 84 см"
        result = parser.parse(text)
        
        assert result['waist'] == 84
    
    def test_parse_food_with_calories(self, parser):
        """Тест парсинга еды с калориями"""
        text = "Еда: Сэндвич 450 ккал, яблоко 52 ккал"
        result = parser.parse(text)
        
        assert result['food'] is not None
        assert len(result['food']) == 2
        assert result['food'][0]['description'] == "Сэндвич"
        assert result['food'][0]['kcal'] == 450
        assert result['food'][1]['description'] == "яблоко"
        assert result['food'][1]['kcal'] == 52
    
    def test_parse_food_without_calories(self, parser):
        """Тест парсинга еды без калорий (для AI оценки)"""
        text = "Еда: Сэндвич из Starbucks, macaron"
        result = parser.parse(text)
        
        assert result['food'] is not None
        assert len(result['food']) == 1
        assert "Starbucks" in result['food'][0]['description']
        assert "macaron" in result['food'][0]['description']
        assert result['food'][0]['kcal'] is None  # Нет калорий - нужна AI оценка
    
    def test_parse_complex_entry(self, parser):
        """Тест парсинга сложной записи"""
        text = """
        Сон: 22:30-04:00 и с 06:30-07:30
        Тренировка: зал 60 мин
        Шаги: 8500
        Еда: Сэндвич 450 ккал, банан 89 ккал
        Вес: 69.3 кг
        Талия: 84 см
        """
        result = parser.parse(text)
        
        assert result['sleep'] is not None
        assert result['workouts'] is not None
        assert result['steps'] == 8500
        assert result['food'] is not None
        assert result['weight'] == 69.3
        assert result['waist'] == 84
    
    def test_parse_empty_text(self, parser):
        """Тест парсинга пустого текста"""
        result = parser.parse("")
        
        assert result['sleep'] is None
        assert result['workouts'] is None
        assert result['steps'] is None
        assert result['food'] is None
        assert result['weight'] is None
        assert result['waist'] is None
    
    def test_parse_multiple_workouts(self, parser):
        """Тест парсинга нескольких тренировок"""
        text = "Тренировка: зал 60 мин, бег 30 минут"
        result = parser.parse(text)
        
        assert len(result['workouts']) == 2
        assert result['workouts'][0]['type'] == WorkoutType.GYM
        assert result['workouts'][1]['type'] == WorkoutType.RUNNING
