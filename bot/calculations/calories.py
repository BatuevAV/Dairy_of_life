"""
Calorie calculations module
BMR, steps, workouts, balance
"""
from bot.database.models import User, DayEntry, WorkoutType


def calculate_bmr(weight: float, height: int, age: int, gender: str = "male") -> float:
    """
    Calculate Basal Metabolic Rate using Mifflin-St Jeor equation
    
    Args:
        weight: Weight in kg
        height: Height in cm
        age: Age in years
        gender: "male" or "female"
    
    Returns:
        BMR in kcal/day
    """
    # Mifflin-St Jeor: BMR = 10*weight + 6.25*height - 5*age + s
    # s = +5 for males, -161 for females
    s = 5 if gender.lower() == "male" else -161
    bmr = 10 * weight + 6.25 * height - 5 * age + s
    return round(bmr, 2)


def calculate_steps_kcal(steps: int, step_coef: float = 0.026) -> float:
    """
    Calculate calories burned from steps
    
    Args:
        steps: Number of steps
        step_coef: Calories per step (default 0.026)
    
    Returns:
        Calories burned from steps
    """
    if not steps or steps < 0:
        return 0.0
    return round(steps * step_coef, 2)


def calculate_workout_kcal(
    workout_type: WorkoutType,
    minutes: int,
    user: User,
    manual_kcal: float = None
) -> float:
    """
    Calculate calories burned from workout
    
    Args:
        workout_type: Type of workout
        minutes: Duration in minutes
        user: User object with kcal_per_hour coefficients
        manual_kcal: Manual calories if provided (takes priority)
    
    Returns:
        Calories burned from workout
    """
    # If manual calories provided, use them
    if manual_kcal is not None and manual_kcal > 0:
        return round(manual_kcal, 2)
    
    if not minutes or minutes <= 0:
        return 0.0
    
    # Get kcal/hour based on workout type
    kcal_per_hour_map = {
        WorkoutType.GYM: user.gym_kcal_per_hour,
        WorkoutType.SWIMMING: user.swim_kcal_per_hour,
        WorkoutType.RUNNING: user.running_kcal_per_hour,
        WorkoutType.CYCLING: user.cycling_kcal_per_hour,
        WorkoutType.OTHER: user.gym_kcal_per_hour  # Default to gym
    }
    
    kcal_per_hour = kcal_per_hour_map.get(workout_type, user.gym_kcal_per_hour)
    kcal = (minutes / 60) * kcal_per_hour
    
    return round(kcal, 2)


def calculate_total_burned(
    bmr: float,
    kcal_steps: float,
    kcal_workout: float
) -> float:
    """
    Calculate total calories burned
    
    Args:
        bmr: Basal metabolic rate
        kcal_steps: Calories from steps
        kcal_workout: Calories from workout
    
    Returns:
        Total calories burned
    """
    total = (bmr or 0) + (kcal_steps or 0) + (kcal_workout or 0)
    return round(total, 2)


def calculate_balance(kcal_eaten: float, kcal_burned: float) -> float:
    """
    Calculate calorie balance (eaten - burned)
    
    Args:
        kcal_eaten: Calories consumed
        kcal_burned: Total calories burned
    
    Returns:
        Calorie balance (positive = surplus, negative = deficit)
    """
    balance = (kcal_eaten or 0) - (kcal_burned or 0)
    return round(balance, 2)


def update_day_entry_calculations(entry: DayEntry, user: User) -> DayEntry:
    """
    Update all calculated fields in a DayEntry
    
    Args:
        entry: DayEntry object to update
        user: User object with profile data
    
    Returns:
        Updated DayEntry object
    """
    # Get weight (from entry or last known)
    weight = entry.weight if entry.weight else 75.0  # Default fallback
    
    # Calculate BMR
    entry.bmr = calculate_bmr(
        weight=weight,
        height=user.height,
        age=user.age,
        gender=user.gender
    )
    
    # Calculate steps calories
    entry.kcal_steps = calculate_steps_kcal(
        steps=entry.steps or 0,
        step_coef=user.step_kcal_coef
    )
    
    # Calculate workout calories
    if entry.workout_type and entry.workout_minutes:
        entry.kcal_workout = calculate_workout_kcal(
            workout_type=entry.workout_type,
            minutes=entry.workout_minutes,
            user=user,
            manual_kcal=entry.workout_kcal_manual
        )
    else:
        entry.kcal_workout = 0.0
    
    # Calculate total burned
    entry.kcal_burned_total = calculate_total_burned(
        bmr=entry.bmr,
        kcal_steps=entry.kcal_steps,
        kcal_workout=entry.kcal_workout
    )
    
    # Calculate balance
    entry.kcal_balance = calculate_balance(
        kcal_eaten=entry.kcal_eaten or 0,
        kcal_burned=entry.kcal_burned_total
    )
    
    return entry
