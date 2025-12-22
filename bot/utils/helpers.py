"""
Helper utilities
"""
from datetime import date, datetime, timedelta
from typing import Optional
import pytz


def format_date(d: date) -> str:
    """Format date as YYYY-MM-DD"""
    return d.strftime('%Y-%m-%d')


def format_datetime(dt: datetime) -> str:
    """Format datetime"""
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def parse_date(date_str: str) -> Optional[date]:
    """Parse date from string"""
    formats = ['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y']
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def get_date_range(days: int, end_date: date = None) -> tuple[date, date]:
    """Get date range for last N days"""
    if end_date is None:
        end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)
    return start_date, end_date


def format_sleep_time(hours: float) -> str:
    """Format sleep hours as HH:MM"""
    h = int(hours)
    m = int((hours - h) * 60)
    return f"{h}ч {m}мин" if m > 0 else f"{h}ч"


def format_calories(kcal: float) -> str:
    """Format calories with sign"""
    if kcal > 0:
        return f"+{kcal:.0f}"
    return f"{kcal:.0f}"


def get_today_in_timezone(tz_str: str = "Asia/Bangkok") -> date:
    """Get today's date in specified timezone"""
    tz = pytz.timezone(tz_str)
    return datetime.now(tz).date()


def sleep_duration_from_range(start: str, end: str) -> float:
    """
    Calculate sleep duration from time range
    Args:
        start: HH:MM
        end: HH:MM
    Returns:
        Duration in hours
    """
    try:
        start_h, start_m = map(int, start.split(':'))
        end_h, end_m = map(int, end.split(':'))
        
        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m
        
        # Handle overnight
        if end_minutes < start_minutes:
            end_minutes += 24 * 60
        
        duration_minutes = end_minutes - start_minutes
        return round(duration_minutes / 60, 2)
    except:
        return 0.0
