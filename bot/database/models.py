"""
Database models for Telegram Bot - Food and Activity Diary
"""
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, Text, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


class InputMode(enum.Enum):
    """Input mode: free text or guided step-by-step"""
    FREE = "free"
    GUIDED = "guided"


class WorkoutType(enum.Enum):
    """Workout types"""
    GYM = "gym"
    SWIMMING = "swimming"
    RUNNING = "running"
    CYCLING = "cycling"
    OTHER = "other"


class MealType(enum.Enum):
    """Meal types"""
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"


class User(Base):
    """User profile and settings"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id = Column(Integer, unique=True, nullable=False, index=True)
    
    # Profile data
    gender = Column(String(10), default="male")  # male/female
    age = Column(Integer, default=28)
    height = Column(Integer, default=179)  # cm
    
    # User goals and medical info
    goal = Column(Text, nullable=True)  # User's fitness goal (lose weight, maintain, gain muscle, etc.)
    medical_recommendations = Column(Text, nullable=True)  # Medical restrictions or recommendations
    
    # Settings
    input_mode = Column(Enum(InputMode), default=InputMode.GUIDED)
    timezone = Column(String(50), default="Asia/Bangkok")
    
    # Calculation coefficients
    step_kcal_coef = Column(Float, default=0.026)  # kcal per step
    gym_kcal_per_hour = Column(Float, default=375)
    swim_kcal_per_hour = Column(Float, default=500)
    running_kcal_per_hour = Column(Float, default=600)
    cycling_kcal_per_hour = Column(Float, default=450)
    
    # Reminders
    reminder_enabled = Column(Boolean, default=True)
    reminder_time = Column(String(5), default="21:00")  # HH:MM (deprecated, kept for compatibility)
    
    # Notification settings (new)
    notifications_enabled = Column(Boolean, default=True)
    breakfast_time = Column(String(5), default="08:00")  # HH:MM
    lunch_time = Column(String(5), default="13:00")  # HH:MM
    dinner_time = Column(String(5), default="19:00")  # HH:MM
    evening_reminder_time = Column(String(5), default="21:00")  # HH:MM
    
    # Access control (for white-list mode)
    is_owner = Column(Boolean, default=False)
    is_allowed = Column(Boolean, default=False)
    allowed_by = Column(Integer, nullable=True)  # User ID who allowed this user
    
    # AI usage limits
    ai_requests_today = Column(Integer, default=0)
    ai_requests_limit = Column(Integer, default=30)  # Per day
    last_ai_request = Column(DateTime, nullable=True)
    
    # Photo settings
    save_photos = Column(Boolean, default=False)  # Save photos to DB (privacy setting)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    day_entries = relationship("DayEntry", back_populates="user", cascade="all, delete-orphan")
    meal_entries = relationship("MealEntry", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(telegram_id={self.telegram_user_id}, age={self.age}, height={self.height})>"


class DayEntry(Base):
    """Daily entry with all data for one day"""
    __tablename__ = "day_entries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    entry_date = Column(Date, nullable=False, index=True)
    
    # Body metrics
    weight = Column(Float, nullable=True)  # kg
    waist = Column(Float, nullable=True)  # cm
    
    # Sleep
    sleep_hours = Column(Float, nullable=True)
    sleep_start = Column(String(5), nullable=True)  # HH:MM
    sleep_end = Column(String(5), nullable=True)  # HH:MM
    
    # Activity
    steps = Column(Integer, nullable=True)
    
    # Workout
    workout_type = Column(Enum(WorkoutType), nullable=True)
    workout_minutes = Column(Integer, nullable=True)
    workout_kcal_manual = Column(Float, nullable=True)  # Manual calories if provided
    
    # Food intake
    kcal_eaten = Column(Float, nullable=True)
    protein = Column(Float, nullable=True)  # grams
    fat = Column(Float, nullable=True)  # grams
    carbs = Column(Float, nullable=True)  # grams
    
    # AI estimation metadata
    food_ai_estimated = Column(Boolean, default=False)
    food_ai_model = Column(String(50), nullable=True)  # Model used for estimation
    food_ai_confidence = Column(Float, nullable=True)  # 0.0 to 1.0
    food_items_json = Column(Text, nullable=True)  # JSON array of food items
    
    # Photo recognition metadata
    photo_analyzed = Column(Boolean, default=False)  # Was photo used
    photo_file_id = Column(String(200), nullable=True)  # Telegram file_id (if user wants to save)
    photo_description = Column(Text, nullable=True)  # What AI saw on photo
    photo_clarifications_json = Column(Text, nullable=True)  # JSON of Q&A
    food_description = Column(Text, nullable=True)  # Human-readable food description
    
    # Raw data
    raw_text = Column(Text, nullable=True)  # Original free-form text input
    notes = Column(Text, nullable=True)  # Additional notes
    
    # Calculated fields (computed on save/update)
    bmr = Column(Float, nullable=True)
    kcal_steps = Column(Float, nullable=True)
    kcal_workout = Column(Float, nullable=True)
    kcal_burned_total = Column(Float, nullable=True)
    kcal_balance = Column(Float, nullable=True)  # eaten - burned
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="day_entries")
    
    # Unique constraint: one entry per user per day
    __table_args__ = (
        UniqueConstraint('user_id', 'entry_date', name='uix_user_date'),
    )
    
    def __repr__(self):
        return f"<DayEntry(date={self.entry_date}, kcal_eaten={self.kcal_eaten}, balance={self.kcal_balance})>"


class MealEntry(Base):
    """Individual meal entry - allows multiple meals per day"""
    __tablename__ = "meal_entries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    day_entry_id = Column(Integer, ForeignKey("day_entries.id"), nullable=True)  # Link to day entry if exists
    
    entry_date = Column(Date, nullable=False, index=True)
    meal_type = Column(Enum(MealType), nullable=False)
    meal_time = Column(String(5), nullable=True)  # HH:MM when meal was consumed
    
    # Food intake
    kcal = Column(Float, nullable=True)
    protein = Column(Float, nullable=True)  # grams
    fat = Column(Float, nullable=True)  # grams
    carbs = Column(Float, nullable=True)  # grams
    
    # AI estimation metadata
    food_ai_estimated = Column(Boolean, default=False)
    food_ai_model = Column(String(50), nullable=True)
    food_ai_confidence = Column(Float, nullable=True)
    food_items_json = Column(Text, nullable=True)  # JSON array of food items
    
    # Photo recognition
    photo_analyzed = Column(Boolean, default=False)
    photo_file_id = Column(String(200), nullable=True)
    photo_description = Column(Text, nullable=True)
    
    # Text data
    food_description = Column(Text, nullable=True)  # Human-readable description
    raw_text = Column(Text, nullable=True)  # Original input
    notes = Column(Text, nullable=True)
    
    # Recipe info (if meal was from suggested recipe)
    from_recipe = Column(Boolean, default=False)
    recipe_name = Column(String(200), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="meal_entries")
    
    def __repr__(self):
        return f"<MealEntry(date={self.entry_date}, type={self.meal_type}, kcal={self.kcal})>"


class ParseLog(Base):
    """Log of free-text parsing attempts for debugging and improvement"""
    __tablename__ = "parse_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    raw_text = Column(Text, nullable=False)
    parsed_fields = Column(Text, nullable=True)  # JSON string of parsed data
    missing_fields = Column(Text, nullable=True)  # List of fields not recognized
    
    confirmed = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<ParseLog(id={self.id}, confirmed={self.confirmed})>"
