"""
Free-text parser for extracting structured data from user messages
Supports Russian and English text
"""
import re
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
import pytz

from bot.database.models import WorkoutType


class FreeTextParser:
    """Parser for free-form text input"""
    
    def __init__(self, timezone: str = "Asia/Bangkok"):
        self.timezone = pytz.timezone(timezone)
    
    def parse(self, text: str) -> Tuple[Dict, List[str]]:
        """
        Parse free-form text into structured data
        
        Args:
            text: User's message text
        
        Returns:
            Tuple of (parsed_data dict, missing_fields list)
        """
        text_lower = text.lower()
        parsed = {}
        missing = []
        
        # Parse date
        parsed['date'] = self._parse_date(text_lower)
        
        # Parse weight
        weight = self._parse_weight(text_lower)
        if weight:
            parsed['weight'] = weight
        
        # Parse waist
        waist = self._parse_waist(text_lower)
        if waist:
            parsed['waist'] = waist
        
        # Parse sleep
        sleep_data = self._parse_sleep(text_lower)
        if sleep_data:
            parsed['sleep'] = sleep_data
        
        # Parse steps
        steps = self._parse_steps(text_lower)
        if steps:
            parsed['steps'] = steps
        
        # Parse workout
        workout_data = self._parse_workout(text_lower)
        if workout_data:
            parsed['workout'] = workout_data
        
        # Parse food/calories
        food_data = self._parse_food(text_lower, text)
        if food_data:
            parsed['food'] = food_data
        
        # Fallback: if only date found and text is short, treat entire text as food description
        if 'food' not in parsed and len(parsed) <= 1:  # Only date or empty
            # Check if text doesn't contain other field keywords
            other_keywords = ['сон', 'sleep', 'шаг', 'step', 'трен', 'workout', 'вес', 'weight', 'талия', 'waist']
            has_other_fields = any(keyword in text_lower for keyword in other_keywords)
            
            if not has_other_fields and len(text.strip()) > 3:
                # Remove date words
                description = text.strip()
                date_words = ['сегодня', 'вчера', 'позавчера', 'today', 'yesterday']
                for word in date_words:
                    description = re.sub(r'\b' + word + r'\b', '', description, flags=re.IGNORECASE)
                description = description.strip()
                
                if description and len(description) > 3:
                    parsed['food'] = {'description': description}
        
        # Determine missing critical fields
        if 'sleep' not in parsed:
            missing.append('сон')
        if 'steps' not in parsed:
            missing.append('шаги')
        if 'food' not in parsed:
            missing.append('еда/калории')
        
        return parsed, missing
    
    def _parse_date(self, text: str) -> date:
        """Parse date from text, default to today"""
        # Check for explicit date patterns
        date_patterns = [
            r'(\d{4})-(\d{2})-(\d{2})',  # YYYY-MM-DD
            r'(\d{2})\.(\d{2})\.(\d{4})',  # DD.MM.YYYY
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    if '-' in match.group():
                        return datetime.strptime(match.group(), '%Y-%m-%d').date()
                    else:
                        return datetime.strptime(match.group(), '%d.%m.%Y').date()
                except ValueError:
                    pass
        
        # Check for relative dates
        if 'вчера' in text or 'yesterday' in text:
            return date.today() - timedelta(days=1)
        if 'позавчера' in text:
            return date.today() - timedelta(days=2)
        
        # Default to today
        return date.today()
    
    def _parse_weight(self, text: str) -> Optional[float]:
        """Parse weight in kg"""
        patterns = [
            r'вес[:\s]*(\d+(?:\.\d+)?)\s*кг',
            r'weight[:\s]*(\d+(?:\.\d+)?)\s*kg',
            r'(\d+(?:\.\d+)?)\s*кг',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    weight = float(match.group(1))
                    if 40 <= weight <= 200:  # Sanity check
                        return weight
                except ValueError:
                    pass
        return None
    
    def _parse_waist(self, text: str) -> Optional[float]:
        """Parse waist measurement in cm"""
        patterns = [
            r'талия[:\s]*(\d+(?:\.\d+)?)\s*см',
            r'waist[:\s]*(\d+(?:\.\d+)?)\s*cm',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    waist = float(match.group(1))
                    if 50 <= waist <= 150:  # Sanity check
                        return waist
                except ValueError:
                    pass
        return None
    
    def _parse_sleep(self, text: str) -> Optional[Dict]:
        """Parse sleep hours or time range"""
        # Pattern: HH:MM-HH:MM (possibly multiple ranges with +)
        time_range_pattern = r'(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})'
        ranges = re.findall(time_range_pattern, text)
        
        if ranges:
            total_hours = 0
            for start_h, start_m, end_h, end_m in ranges:
                start_minutes = int(start_h) * 60 + int(start_m)
                end_minutes = int(end_h) * 60 + int(end_m)
                
                # Handle overnight sleep
                if end_minutes < start_minutes:
                    end_minutes += 24 * 60
                
                duration_minutes = end_minutes - start_minutes
                total_hours += duration_minutes / 60
            
            return {
                'hours': round(total_hours, 2),
                'ranges': text  # Store original text
            }
        
        # Pattern: just hours
        hour_patterns = [
            r'сон[:\s]*(\d+(?:\.\d+)?)\s*ч',
            r'sleep[:\s]*(\d+(?:\.\d+)?)\s*h',
            r'спал[:\s]*(\d+(?:\.\d+)?)\s*ч',
        ]
        
        for pattern in hour_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    hours = float(match.group(1))
                    if 0 <= hours <= 24:
                        return {'hours': hours}
                except ValueError:
                    pass
        
        return None
    
    def _parse_steps(self, text: str) -> Optional[int]:
        """Parse step count"""
        patterns = [
            r'шаги?[:\s]*(\d+)',
            r'steps?[:\s]*(\d+)',
            r'(\d+)\s*шаг',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    steps = int(match.group(1))
                    if 0 <= steps <= 100000:  # Sanity check
                        return steps
                except ValueError:
                    pass
        return None
    
    def _parse_workout(self, text: str) -> Optional[Dict]:
        """Parse workout type, duration, and optional manual calories"""
        workout_data = {}
        
        # Detect workout type
        workout_keywords = {
            WorkoutType.GYM: ['зал', 'gym', 'тренажер', 'качалк'],
            WorkoutType.SWIMMING: ['плавани', 'бассейн', 'swim'],
            WorkoutType.RUNNING: ['бег', 'run', 'пробежк'],
            WorkoutType.CYCLING: ['велосипед', 'cycling', 'bike'],
        }
        
        detected_type = None
        for workout_type, keywords in workout_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    detected_type = workout_type
                    break
            if detected_type:
                break
        
        if detected_type:
            workout_data['type'] = detected_type
            
            # Parse duration
            duration_patterns = [
                r'(\d+)\s*мин',
                r'(\d+)\s*min',
            ]
            
            for pattern in duration_patterns:
                match = re.search(pattern, text)
                if match:
                    try:
                        minutes = int(match.group(1))
                        if 0 <= minutes <= 600:
                            workout_data['minutes'] = minutes
                            break
                    except ValueError:
                        pass
            
            # Parse manual calories (optional)
            kcal_patterns = [
                r'тренировка[:\s]*(\d+)\s*ккал',
                r'workout[:\s]*(\d+)\s*kcal',
            ]
            
            for pattern in kcal_patterns:
                match = re.search(pattern, text)
                if match:
                    try:
                        kcal = float(match.group(1))
                        workout_data['kcal_manual'] = kcal
                        break
                    except ValueError:
                        pass
        
        return workout_data if workout_data else None
    
    def _parse_food(self, text_lower: str, text_original: str) -> Optional[Dict]:
        """Parse food/calorie information"""
        food_data = {}
        
        # Parse meal type from text
        meal_type_patterns = [
            (r'на завтрак|завтрак|breakfast', 'breakfast'),
            (r'на обед|обед|lunch', 'lunch'),
            (r'на ужин|ужин|dinner', 'dinner'),
            (r'перекус|snack', 'snack'),
        ]
        
        for pattern, meal_type in meal_type_patterns:
            if re.search(pattern, text_lower):
                food_data['meal_type'] = meal_type
                break
        
        # Parse total calories
        kcal_patterns = [
            r'ккал[:\s]*(\d+)',
            r'калори[ий][:\s]*(\d+)',
            r'kcal[:\s]*(\d+)',
            r'(\d+)\s*ккал',
        ]
        
        for pattern in kcal_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    kcal = float(match.group(1))
                    if 0 <= kcal <= 10000:
                        food_data['kcal'] = kcal
                        break
                except ValueError:
                    pass
        
        # Parse macros (БЖУ)
        # Pattern: БЖУ: 150/60/180 or Б:150 Ж:60 У:180
        macro_patterns = [
            r'бжу[:\s]*(\d+)\s*/\s*(\d+)\s*/\s*(\d+)',
            r'б[:\s]*(\d+)\s*ж[:\s]*(\d+)\s*у[:\s]*(\d+)',
            r'protein[:\s]*(\d+)\s*fat[:\s]*(\d+)\s*carbs?[:\s]*(\d+)',
        ]
        
        for pattern in macro_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    food_data['protein'] = float(match.group(1))
                    food_data['fat'] = float(match.group(2))
                    food_data['carbs'] = float(match.group(3))
                    break
                except ValueError:
                    pass
        
        # Extract food description (everything between "еда:" and next field)
        food_desc_patterns = [
            r'еда[:\s]*(.+?)(?=вес|шаг|трен|сон|$)',
            r'food[:\s]*(.+?)(?=weight|step|workout|sleep|$)',
            r'(?:съел|поел|ел|ate|had|eaten)[:\s]*(.+?)(?=вес|шаг|трен|сон|ккал|бжу|$)',
        ]
        
        for pattern in food_desc_patterns:
            match = re.search(pattern, text_lower, re.DOTALL)
            if match:
                description = match.group(1).strip()
                # Remove common noise words
                description = re.sub(r'\s+(сегодня|вчера|today|yesterday)\s*', ' ', description).strip()
                if description and len(description) > 3:  # At least 3 chars
                    food_data['description'] = description
                break
        
        return food_data if food_data else None
