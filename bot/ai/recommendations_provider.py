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
    
    async def generate_meal_suggestions(self, user: User, meal_type: str = "breakfast", count: int = 3) -> List[Dict[str, str]]:
        """Generate meal suggestions based on user profile and meal type"""
        user_context = self._build_user_context(user)
        
        meal_names = {
            "breakfast": "завтрака",
            "lunch": "обеда",
            "dinner": "ужина",
            "snack": "перекуса"
        }
        
        meal_name_ru = meal_names.get(meal_type, "приема пищи")
        
        prompt = f"""{user_context}

Задание: Предложи {count} варианта {meal_name_ru} для этого пользователя.

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
            # Return fallback suggestions based on meal type
            return self._get_fallback_suggestions(meal_type)
    
    async def generate_breakfast_suggestions(self, user: User, count: int = 3) -> List[Dict[str, str]]:
        """Generate breakfast suggestions (compatibility wrapper)"""
        return await self.generate_meal_suggestions(user, "breakfast", count)
    
    def _get_fallback_suggestions(self, meal_type: str) -> List[Dict[str, str]]:
        """Get fallback suggestions when AI fails"""
        fallbacks = {
            "breakfast": [
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
            ],
            "lunch": [
                {
                    "name": "Куриная грудка с гречкой",
                    "description": "Сбалансированный белковый обед",
                    "kcal": 450,
                    "protein": 40,
                    "fat": 10,
                    "carbs": 50
                },
                {
                    "name": "Овощной суп с говядиной",
                    "description": "Питательный и легкий",
                    "kcal": 380,
                    "protein": 30,
                    "fat": 12,
                    "carbs": 40
                },
                {
                    "name": "Лосось с киноа и овощами",
                    "description": "Полезные жиры и белок",
                    "kcal": 520,
                    "protein": 35,
                    "fat": 20,
                    "carbs": 45
                }
            ],
            "dinner": [
                {
                    "name": "Запеченная рыба с салатом",
                    "description": "Легкий ужин с белком",
                    "kcal": 350,
                    "protein": 35,
                    "fat": 15,
                    "carbs": 20
                },
                {
                    "name": "Тушеные овощи с индейкой",
                    "description": "Низкокалорийный вариант",
                    "kcal": 320,
                    "protein": 32,
                    "fat": 10,
                    "carbs": 25
                },
                {
                    "name": "Творожная запеканка",
                    "description": "Белковый ужин",
                    "kcal": 280,
                    "protein": 28,
                    "fat": 8,
                    "carbs": 22
                }
            ],
            "snack": [
                {
                    "name": "Греческий йогурт с ягодами",
                    "description": "Быстрый белковый перекус",
                    "kcal": 150,
                    "protein": 15,
                    "fat": 3,
                    "carbs": 18
                },
                {
                    "name": "Орехи и сухофрукты",
                    "description": "Энергетический микс",
                    "kcal": 200,
                    "protein": 6,
                    "fat": 12,
                    "carbs": 20
                },
                {
                    "name": "Яблоко с арахисовой пастой",
                    "description": "Полезный и вкусный",
                    "kcal": 180,
                    "protein": 8,
                    "fat": 10,
                    "carbs": 20
                }
            ]
        }
        
        return fallbacks.get(meal_type, fallbacks["snack"])
    
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
