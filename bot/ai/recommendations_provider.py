"""
AI Provider for generating personalized recommendations and recipes
"""
import json
from typing import Dict, List, Optional
from bot.config import settings
from bot.database import User


class RecommendationsProvider:
    """Generate personalized recommendations using AI"""
    
    def __init__(self, provider: str = None):
        """Initialize with AI provider (ollama/gemini)"""
        self.provider = provider or settings.DEFAULT_AI_PROVIDER
        
        if self.provider == "ollama":
            from bot.ai.ollama_provider import OllamaProvider
            self.ai = OllamaProvider()
        elif self.provider == "gemini":
            from bot.ai.gemini_provider import GeminiProvider
            self.ai = GeminiProvider()
        else:
            raise ValueError(f"Unknown AI provider: {self.provider}")
    
    def _build_user_context(self, user: User) -> str:
        """Build user context for AI prompt"""
        gender_ru = "Мужчина" if user.gender == "male" else "Женщина"
        return f"""
Пользователь:
- Пол: {gender_ru}
- Возраст: {user.age} лет
- Рост: {user.height} см
"""
    
    async def generate_brief_recommendation(self, user: User) -> str:
        """Generate brief recommendation after profile setup"""
        user_context = self._build_user_context(user)
        
        prompt = f"""{user_context}

Задание: Дай ОЧЕНЬ КРАТКУЮ рекомендацию (максимум 3-4 предложения) по питанию и тренировкам для этого пользователя.
Будь конкретным и мотивирующим. Не пиши общие фразы."""
        
        try:
            response = await self.ai.generate_text(prompt)
            return response.strip()
        except Exception as e:
            return f"Отлично! Теперь ты можешь начать вести дневник питания и активности. 💪"
    
    async def generate_detailed_nutrition_recommendation(self, user: User) -> str:
        """Generate detailed nutrition recommendation"""
        user_context = self._build_user_context(user)
        
        prompt = f"""{user_context}

Задание: Дай ПОДРОБНУЮ рекомендацию по питанию (5-7 пунктов):
- Оптимальная калорийность
- Соотношение БЖУ (белки/жиры/углеводы)
- Рекомендуемые продукты
- Продукты, которых следует избегать
- Режим питания (количество приемов пищи)
- Питьевой режим
- Дополнительные советы

Формат: используй эмодзи и структурированный текст."""
        
        try:
            response = await self.ai.generate_text(prompt)
            return response.strip()
        except Exception as e:
            return "❌ Ошибка при генерации рекомендации"
    
    async def generate_detailed_workout_recommendation(self, user: User) -> str:
        """Generate detailed workout recommendation"""
        user_context = self._build_user_context(user)
        
        prompt = f"""{user_context}

Задание: Дай ПОДРОБНУЮ рекомендацию по тренировкам (5-7 пунктов):
- Оптимальная частота тренировок
- Рекомендуемые виды активности
- Интенсивность и продолжительность
- Структура тренировки (разминка, основная часть, заминка)
- Предостережения и противопоказания
- Прогрессия нагрузки
- Восстановление между тренировками

Формат: используй эмодзи и структурированный текст."""
        
        try:
            response = await self.ai.generate_text(prompt)
            return response.strip()
        except Exception as e:
            return "❌ Ошибка при генерации рекомендации"
    
    async def generate_breakfast_suggestions(self, user: User, count: int = 3) -> List[Dict[str, str]]:
        """Generate breakfast suggestions based on user profile"""
        user_context = self._build_user_context(user)
        
        prompt = f"""{user_context}

Задание: Предложи {count} варианта завтрака для этого пользователя.

Верни результат СТРОГО в JSON формате (без комментариев и markdown):
[
  {{
    "name": "Название блюда",
    "description": "Краткое описание (1 предложение)",
    "kcal": примерная калорийность (число),
    "protein": граммы белка (число),
    "fat": граммы жира (число),
    "carbs": граммы углеводов (число)
  }},
  ...
]

ВАЖНО: Верни ТОЛЬКО JSON массив, без текста до и после."""
        
        try:
            response = await self.ai.generate_text(prompt)
            # Extract JSON from response
            response = response.strip()
            if response.startswith("```"):
                # Remove markdown code blocks
                lines = response.split('\n')
                response = '\n'.join([l for l in lines if not l.strip().startswith('```')])
            
            suggestions = json.loads(response)
            return suggestions
        except Exception as e:
            # Return fallback suggestions
            return [
                {
                    "name": "Овсяная каша с фруктами",
                    "description": "Классический полезный завтрак",
                    "kcal": 350,
                    "protein": 12,
                    "fat": 8,
                    "carbs": 55
                },
                {
                    "name": "Омлет с овощами",
                    "description": "Белковый завтрак",
                    "kcal": 280,
                    "protein": 20,
                    "fat": 15,
                    "carbs": 10
                },
                {
                    "name": "Творог с медом и орехами",
                    "description": "Быстрый и питательный вариант",
                    "kcal": 320,
                    "protein": 25,
                    "fat": 12,
                    "carbs": 28
                }
            ]
    
    async def generate_recipe(self, dish_name: str, user: User) -> Dict[str, any]:
        """Generate detailed recipe for a dish"""
        user_context = self._build_user_context(user)
        
        prompt = f"""{user_context}

Задание: Создай подробный рецепт для блюда "{dish_name}".

Верни результат СТРОГО в JSON формате:
{{
  "name": "Название блюда",
  "description": "Описание",
  "servings": количество порций (число),
  "cooking_time": время приготовления в минутах (число),
  "ingredients": [
    {{"item": "Название продукта", "amount": "количество"}},
    ...
  ],
  "instructions": [
    "Шаг 1",
    "Шаг 2",
    ...
  ],
  "nutrition": {{
    "kcal": калорийность на порцию,
    "protein": белки в граммах,
    "fat": жиры в граммах,
    "carbs": углеводы в граммах
  }}
}}

ВАЖНО: Верни ТОЛЬКО JSON, без текста до и после."""
        
        try:
            response = await self.ai.generate_text(prompt)
            # Extract JSON
            response = response.strip()
            if response.startswith("```"):
                lines = response.split('\n')
                response = '\n'.join([l for l in lines if not l.strip().startswith('```')])
            
            recipe = json.loads(response)
            return recipe
        except Exception as e:
            return {
                "name": dish_name,
                "description": "Рецепт временно недоступен",
                "servings": 1,
                "cooking_time": 30,
                "ingredients": [],
                "instructions": ["Рецепт в разработке"],
                "nutrition": {
                    "kcal": 0,
                    "protein": 0,
                    "fat": 0,
                    "carbs": 0
                }
            }
