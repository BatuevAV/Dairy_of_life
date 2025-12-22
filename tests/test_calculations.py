"""
Тесты для расчета калорий
"""
import pytest
from bot.calculations.calories import (
    calculate_sleep_hours,
    calculate_bmr,
    calculate_steps_kcal,
    calculate_workout_kcal
)
from bot.database.models import WorkoutType, User
from datetime import time


class TestSleepCalculation:
    """Тесты расчета времени сна"""
    
    def test_simple_sleep(self):
        """Тест простого сна в одну ночь"""
        hours = calculate_sleep_hours([(time(23, 0), time(7, 0))])
        assert hours == 8.0
    
    def test_sleep_across_midnight(self):
        """Тест сна через полночь"""
        hours = calculate_sleep_hours([(time(22, 30), time(6, 30))])
        assert hours == 8.0
    
    def test_multiple_sleep_periods(self):
        """Тест нескольких периодов сна"""
        periods = [
            (time(22, 30), time(4, 0)),
            (time(6, 30), time(7, 30))
        ]
        hours = calculate_sleep_hours(periods)
        assert hours == 6.5  # 5.5 + 1.0
    
    def test_short_nap(self):
        """Тест короткого дневного сна"""
        hours = calculate_sleep_hours([(time(14, 0), time(14, 30))])
        assert hours == 0.5


class TestCalories:
    """Тесты функций расчета калорий"""
    
    @pytest.fixture
    def user(self):
        """Тестовый пользователь"""
        user = User()
        user.gender = "male"
        user.age = 28
        user.height = 179
        user.step_kcal_coef = 0.026
        user.gym_kcal_per_hour = 375
        user.swim_kcal_per_hour = 500
        user.running_kcal_per_hour = 600
        user.cycling_kcal_per_hour = 450
        return user
    
    def test_bmr_male(self):
        """Тест расчета BMR для мужчины"""
        bmr = calculate_bmr(weight=70, height=179, age=28, gender="male")
        # BMR = 10 * 70 + 6.25 * 179 - 5 * 28 + 5 = 1683.75
        assert abs(bmr - 1683.75) < 0.1
    
    def test_bmr_female(self):
        """Тест расчета BMR для женщины"""
        bmr = calculate_bmr(weight=60, height=179, age=28, gender="female")
        # BMR = 10 * 60 + 6.25 * 179 - 5 * 28 - 161 = 1357.75
        assert abs(bmr - 1357.75) < 0.1
    
    def test_steps_calories(self):
        """Тест расчета калорий от шагов"""
        kcal = calculate_steps_kcal(steps=10000, step_coef=0.026)
        assert kcal == 260.0  # 10000 * 0.026
    
    def test_workout_gym(self, user):
        """Тест расчета калорий тренировки в зале"""
        kcal = calculate_workout_kcal(
            workout_type=WorkoutType.GYM,
            minutes=60,
            user=user
        )
        assert kcal == 375.0  # 375 ккал/час * 1 час
    
    def test_workout_swimming(self, user):
        """Тест расчета калорий плавания"""
        kcal = calculate_workout_kcal(
            workout_type=WorkoutType.SWIMMING,
            minutes=45,
            user=user
        )
        assert kcal == 375.0  # 500 * 0.75
    
    def test_workout_running(self, user):
        """Тест расчета калорий бега"""
        kcal = calculate_workout_kcal(
            workout_type=WorkoutType.RUNNING,
            minutes=30,
            user=user
        )
        assert kcal == 300.0  # 600 * 0.5
    
    def test_zero_steps(self):
        """Тест с нулевыми шагами"""
        kcal = calculate_steps_kcal(steps=0)
        assert kcal == 0.0
    
    def test_negative_steps(self):
        """Тест с отрицательными шагами"""
        kcal = calculate_steps_kcal(steps=-100)
        assert kcal == 0.0


class TestSleepCalculation:
    """Тесты расчета времени сна"""
    
    def test_simple_sleep(self):
        """Тест простого сна в одну ночь"""
        hours = calculate_sleep_hours([(time(23, 0), time(7, 0))])
        assert hours == 8.0
    
    def test_sleep_across_midnight(self):
        """Тест сна через полночь"""
        hours = calculate_sleep_hours([(time(22, 30), time(6, 30))])
        assert hours == 8.0
    
    def test_multiple_sleep_periods(self):
        """Тест нескольких периодов сна"""
        periods = [
            (time(22, 30), time(4, 0)),
            (time(6, 30), time(7, 30))
        ]
        hours = calculate_sleep_hours(periods)
        assert hours == 6.5  # 5.5 + 1.0
    
    def test_short_nap(self):
        """Тест короткого дневного сна"""
        hours = calculate_sleep_hours([(time(14, 0), time(14, 30))])
        assert hours == 0.5


class TestCalorieCalculator:
    """Тесты калькулятора калорий"""
    
    @pytest.fixture
    def user(self):
        """Тестовый пользователь"""
        user = User()
        user.gender = "male"
        user.age = 28
        user.height = 179
        user.step_kcal_coef = 0.026
        user.gym_kcal_per_hour = 375
        user.swim_kcal_per_hour = 500
        user.running_kcal_per_hour = 600
        user.cycling_kcal_per_hour = 450
        return user
    
    @pytest.fixture
    def calculator(self, user):
        return CalorieCalculator(user)
    
    def test_bmr_male(self, calculator):
        """Тест расчета BMR для мужчины"""
        bmr = calculator.calculate_bmr(weight=70)
        # BMR = 10 * 70 + 6.25 * 179 - 5 * 28 + 5 = 1683.75
        assert abs(bmr - 1683.75) < 0.1
    
    def test_bmr_female(self, user):
        """Тест расчета BMR для женщины"""
        user.gender = "female"
        calculator = CalorieCalculator(user)
        bmr = calculator.calculate_bmr(weight=60)
        # BMR = 10 * 60 + 6.25 * 179 - 5 * 28 - 161 = 1357.75
        assert abs(bmr - 1357.75) < 0.1
    
    def test_steps_calories(self, calculator):
        """Тест расчета калорий от шагов"""
        kcal = calculator.calculate_steps_calories(steps=10000)
        assert kcal == 10000 * 0.026  # 260
    
    def test_workout_gym(self, calculator):
        """Тест расчета калорий тренировки в зале"""
        kcal = calculator.calculate_workout_calories(
            workout_type=WorkoutType.GYM,
            minutes=60
        )
        assert kcal == 375  # 375 ккал/час * 1 час
    
    def test_workout_swimming(self, calculator):
        """Тест расчета калорий плавания"""
        kcal = calculator.calculate_workout_calories(
            workout_type=WorkoutType.SWIMMING,
            minutes=45
        )
        assert kcal == 375  # 500 * 0.75
    
    def test_workout_running(self, calculator):
        """Тест расчета калорий бега"""
        kcal = calculator.calculate_workout_calories(
            workout_type=WorkoutType.RUNNING,
            minutes=30
        )
        assert kcal == 300  # 600 * 0.5
    
    def test_total_burned_calories(self, calculator):
        """Тест расчета общих потраченных калорий"""
        workouts = [
            {'type': WorkoutType.GYM, 'minutes': 60},
            {'type': WorkoutType.RUNNING, 'minutes': 30}
        ]
        
        total = calculator.calculate_total_burned(
            weight=70,
            steps=10000,
            workouts=workouts
        )
        
        # BMR = 1683.75
        # Шаги = 260
        # Зал = 375
        # Бег = 300
        # Итого = 1683.75 + 260 + 375 + 300 = 2618.75
        assert abs(total - 2618.75) < 0.1
    
    def test_balance_positive(self, calculator):
        """Тест расчета баланса (профицит)"""
        balance = calculator.calculate_balance(
            consumed=2500,
            burned=2000
        )
        assert balance == 500
    
    def test_balance_negative(self, calculator):
        """Тест расчета баланса (дефицит)"""
        balance = calculator.calculate_balance(
            consumed=1800,
            burned=2200
        )
        assert balance == -400
    
    def test_zero_steps(self, calculator):
        """Тест с нулевыми шагами"""
        kcal = calculator.calculate_steps_calories(steps=0)
        assert kcal == 0
    
    def test_no_workouts(self, calculator):
        """Тест без тренировок"""
        total = calculator.calculate_total_burned(
            weight=70,
            steps=0,
            workouts=[]
        )
        # Только BMR
        assert abs(total - 1683.75) < 0.1
