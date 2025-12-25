"""
AI Provider for generating personalized recommendations and recipes
"""
import json
import random
from typing import Dict, List, Optional
from bot.config import settings
from bot.database import User


class RecommendationsProvider:
    """Generate personalized recommendations using AI"""
    
    def __init__(self, provider: str = None):
        """Initialize with AI provider (auto/ollama/gemini)"""
        self.provider = provider or settings.DEFAULT_AI_PROVIDER
        
        if self.provider == "auto" or self.provider == "smart":
            # Use smart provider with automatic fallback
            from bot.ai.smart_provider import SmartAIProvider
            self.ai = SmartAIProvider()
            self.use_smart = True
        elif self.provider == "ollama":
            from bot.ai.ollama_provider import OllamaProvider
            self.ai = OllamaProvider()
            self.use_smart = False
        elif self.provider == "gemini":
            from bot.ai.gemini_provider import GeminiProvider
            self.ai = GeminiProvider()
            self.use_smart = False
        else:
            raise ValueError(f"Unknown AI provider: {self.provider}")
    
    def _build_user_context(self, user: User) -> str:
        """Build user context for AI prompt"""
        gender_ru = "Мужчина" if user.gender == "male" else "Женщина"
        
        context = f"""
Пользователь:
- Пол: {gender_ru}
- Возраст: {user.age} лет
- Рост: {user.height} см
"""
        
        # Add goal if set
        if user.goal:
            context += f"- Цель: {user.goal}\n"
        
        # Add medical recommendations if set
        if user.medical_recommendations:
            context += f"- Врачебные рекомендации/ограничения: {user.medical_recommendations}\n"
        
        return context
    
    async def generate_brief_recommendation(self, user: User) -> str:
        """Generate brief recommendation after profile setup"""
        user_context = self._build_user_context(user)
        
        prompt = f"""{user_context}

Задание: Дай ОЧЕНЬ КРАТКУЮ рекомендацию (максимум 3-4 предложения) по питанию и тренировкам для этого пользователя.

КРИТИЧЕСКИ ВАЖНО:
- Пиши ТОЛЬКО на правильном русском языке
- НИКОГДА не используй английские слова в русском тексте
- НИКОГДА не искажай русские слова
- НЕ используй транслитерацию (например, НЕ пиши "Focus", пиши "фокус")
- НЕ смешивай языки в одном предложении

Примеры НЕПРАВИЛЬНО:
❌ "Focus наLean Protein"
❌ "Heavy Weight Training"
❌ "более重ая упражнения"
❌ "голarticULATE мышечная масса"

Примеры ПРАВИЛЬНО:
✅ "Сфокусируйся на белковой пище"
✅ "Тренировки с большим весом"
✅ "Более тяжелые упражнения"

Будь конкретным и мотивирующим. Не пиши общие фразы.
ОБЯЗАТЕЛЬНО учитывай цель пользователя и врачебные рекомендации, если они указаны."""
        
        try:
            response = await self.ai.generate_text(prompt)
            return response.strip()
        except Exception as e:
            # Return default recommendation on error
            return "💪 Отлично! Начни вести дневник питания и активности. Следи за балансом калорий, старайся делать хотя бы 8000 шагов в день и тренируйся 3-4 раза в неделю. Ты на правильном пути!"
    
    async def generate_detailed_nutrition_recommendation(self, user: User) -> str:
        """Generate detailed nutrition recommendation"""
        user_context = self._build_user_context(user)
        
        prompt = f"""{user_context}

Задание: Дай ПОДРОБНУЮ рекомендацию по питанию (5-7 пунктов):
- Оптимальная калорийность
- Соотношение БЖУ (белки/жиры/углеводы)

ВАЖНО: Пиши ТОЛЬКО на правильном русском языке, НЕ искажай слова!
- Рекомендуемые продукты
- Продукты, которых следует избегать
- Режим питания (количество приемов пищи)
- Питьевой режим
- Дополнительные советы

ВАЖНО: ОБЯЗАТЕЛЬНО учитывай цель пользователя и врачебные рекомендации, если они указаны!
Если есть ограничения - не рекомендуй запрещённые продукты.

Формат: используй эмодзи и структурированный текст."""
        
        try:
            response = await self.ai.generate_text(prompt)
            return response.strip()
        except Exception as e:
            # Return default nutrition advice
            gender_ru = "мужчин" if user.gender == "male" else "женщин"
            goal_text = f"\n🎯 <b>С учетом твоей цели: {user.goal}</b>\n" if user.goal else ""
            medical_text = f"\n🏥 <b>Учитываем: {user.medical_recommendations}</b>\n" if user.medical_recommendations else ""
            
            return f"""🥗 <b>Рекомендации по питанию</b>
{goal_text}{medical_text}
📊 <b>Калорийность и БЖУ:</b>
• Для {gender_ru} {user.age} лет: 2000-2500 ккал в день
• Белки: 25-30% (1.5-2г на кг веса)
• Жиры: 25-30% (преимущественно ненасыщенные)
• Углеводы: 40-50% (сложные углеводы)

✅ <b>Рекомендуемые продукты:</b>
• Белковые: курица, рыба, яйца, творог
• Углеводы: гречка, овсянка, киноа, цельнозерновой хлеб
• Овощи и фрукты: 400-500г в день
• Полезные жиры: орехи, авокадо, оливковое масло

❌ <b>Ограничить:</b>
• Быстрые углеводы: сладости, белый хлеб
• Жареное и фастфуд
• Газированные напитки

⏰ <b>Режим:</b>
• 3-4 приема пищи в день
• Завтрак обязателен (30% дневной калорийности)
• Ужин за 2-3 часа до сна

💧 <b>Питьевой режим:</b>
• 30-40 мл на кг веса (около 2-2.5 литров в день)

💡 <b>Дополнительно:</b>
• Ведите дневник питания (вы уже это делаете!)
• Взвешивайтесь 1 раз в неделю утром
• Делайте разгрузочные дни при необходимости"""
    
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

ВАЖНО: Пиши ТОЛЬКО на правильном русском языке, НЕ искажай слова!
ОБЯЗАТЕЛЬНО учитывай цель пользователя и врачебные рекомендации, если они указаны!
Если есть медицинские ограничения - адаптируй рекомендации под них.

Формат: используй эмодзи и структурированный текст."""
        
        try:
            response = await self.ai.generate_text(prompt)
            return response.strip()
        except Exception as e:
            # Return default workout advice
            gender_ru = "мужчин" if user.gender == "male" else "женщин"
            goal_text = f"\n🎯 <b>С учетом твоей цели: {user.goal}</b>\n" if user.goal else ""
            medical_text = f"\n🏥 <b>Учитываем: {user.medical_recommendations}</b>\n" if user.medical_recommendations else ""
            
            return f"""💪 <b>Рекомендации по тренировкам</b>
{goal_text}{medical_text}
📅 <b>Частота тренировок:</b>
• 3-4 раза в неделю для начинающих
• 4-5 раз в неделю для продолжающих
• Минимум 1 день отдыха между тренировками

🏃 <b>Виды активности:</b>
• Кардио: бег, плавание, велосипед (150 мин в неделю)
• Силовые: зал, TRX, упражнения с весом тела
• Растяжка: йога, стретчинг
• Ежедневная активность: 8000-10000 шагов

⏱ <b>Продолжительность:</b>
• Кардио: 30-45 минут
• Силовые: 45-60 минут
• Разминка: 10 минут
• Заминка: 10 минут

📋 <b>Структура тренировки:</b>
1. Разминка (суставная гимнастика, легкое кардио)
2. Основная часть (силовые/кардио)
3. Заминка (растяжка)

⚠️ <b>Важно:</b>
• Начинайте с легких весов
• Следите за техникой выполнения
• При болях - остановитесь
• Пейте воду во время тренировки

📈 <b>Прогрессия:</b>
• Увеличивайте нагрузку постепенно (10% в неделю)
• Ведите дневник тренировок
• Периодизация: 3-4 недели нагрузка, 1 неделя отдых

😴 <b>Восстановление:</b>
• Сон 7-8 часов
• Белок после тренировки (30г в течение часа)
• Массаж, баня (опционально)
• Не тренируйте одну группу мышц 2 дня подряд"""
    
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

КРИТИЧЕСКИ ВАЖНО:
- Пиши ТОЛЬКО на правильном русском языке
- НИКОГДА не используй английские буквы в русских словах
- НИКОГДА не сокращай и не искажай слова
- Пиши полные правильные названия блюд

ВАЖНО: ОБЯЗАТЕЛЬНО учитывай цель пользователя и врачебные рекомендации, если они указаны!
Если есть ограничения по продуктам - НЕ предлагай их.

Примеры ПРАВИЛЬНЫХ названий:
✅ Салат с тунцом (НЕ "Сalatка с тунceanой")
✅ Гречка с курицей (НЕ "Грязь на тарте")
✅ Овощной суп (НЕ "Овоshное суп")

Верни результат СТРОГО в JSON формате (без комментариев и markdown):
[
  {{
    "name": "Название блюда на правильном русском",
    "description": "Краткое описание (1 предложение) на правильном русском",
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
        all_suggestions = {
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
                },
                {
                    "name": "Сырники со сметаной",
                    "description": "Вкусный белковый завтрак",
                    "kcal": 380,
                    "protein": 22,
                    "fat": 14,
                    "carbs": 42
                },
                {
                    "name": "Гранола с йогуртом",
                    "description": "Энергетический завтрак",
                    "kcal": 340,
                    "protein": 15,
                    "fat": 10,
                    "carbs": 48
                },
                {
                    "name": "Блинчики с творогом",
                    "description": "Сытный завтрак на выходные",
                    "kcal": 420,
                    "protein": 18,
                    "fat": 16,
                    "carbs": 52
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
                },
                {
                    "name": "Паста с курицей и грибами",
                    "description": "Сытный итальянский обед",
                    "kcal": 480,
                    "protein": 32,
                    "fat": 14,
                    "carbs": 58
                },
                {
                    "name": "Плов с индейкой",
                    "description": "Восточное блюдо с мясом птицы",
                    "kcal": 460,
                    "protein": 28,
                    "fat": 16,
                    "carbs": 54
                },
                {
                    "name": "Рыбные котлеты с рисом",
                    "description": "Легкий рыбный обед",
                    "kcal": 420,
                    "protein": 34,
                    "fat": 12,
                    "carbs": 48
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
                },
                {
                    "name": "Куриные котлеты на пару",
                    "description": "Диетический ужин",
                    "kcal": 310,
                    "protein": 36,
                    "fat": 12,
                    "carbs": 18
                },
                {
                    "name": "Омлет с брокколи",
                    "description": "Быстрый белковый ужин",
                    "kcal": 260,
                    "protein": 24,
                    "fat": 14,
                    "carbs": 12
                },
                {
                    "name": "Тунец с овощным салатом",
                    "description": "Легкий средиземноморский ужин",
                    "kcal": 290,
                    "protein": 30,
                    "fat": 10,
                    "carbs": 16
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
                },
                {
                    "name": "Протеиновый батончик",
                    "description": "Удобный перекус",
                    "kcal": 190,
                    "protein": 12,
                    "fat": 6,
                    "carbs": 22
                },
                {
                    "name": "Творог с бананом",
                    "description": "Белковый перекус с углеводами",
                    "kcal": 170,
                    "protein": 16,
                    "fat": 4,
                    "carbs": 20
                },
                {
                    "name": "Хумус с овощными палочками",
                    "description": "Легкий средиземноморский перекус",
                    "kcal": 140,
                    "protein": 6,
                    "fat": 8,
                    "carbs": 14
                }
            ]
        }
        
        suggestions = all_suggestions.get(meal_type, all_suggestions["snack"])
        # Выбираем 3 случайных варианта без повторений
        return random.sample(suggestions, min(3, len(suggestions)))
    
    async def generate_recipe(self, dish_name: str, user: User) -> Dict[str, any]:
        """Generate detailed recipe for a dish"""
        user_context = self._build_user_context(user)
        
        prompt = f"""{user_context}

Задание: Создай подробный рецепт для блюда "{dish_name}".

ВАЖНО: 
- Пиши ТОЛЬКО на правильном русском языке, НЕ искажай слова!
- ОБЯЗАТЕЛЬНО учитывай цель пользователя и врачебные рекомендации!
- Если есть ограничения по продуктам - адаптируй рецепт или предложи альтернативу.

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
            # Log the error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"AI recipe generation failed for '{dish_name}': {str(e)}")
            logger.error(f"AI provider: {self.provider}")
            # Return fallback recipe based on dish name
            return self._get_fallback_recipe(dish_name)
    
    def _get_fallback_recipe(self, dish_name: str) -> Dict[str, any]:
        """Get fallback recipe when AI fails"""
        # Try to match common dishes
        dish_lower = dish_name.lower()
        
        if any(word in dish_lower for word in ["рыба", "лосось", "тунец", "треска", "семга", "форель"]):
            return {
                "name": dish_name,
                "description": "Полезное блюдо с высоким содержанием белка и омега-3",
                "servings": 2,
                "cooking_time": 30,
                "ingredients": [
                    {"item": "Филе рыбы (лосось/треска)", "amount": "400 г"},
                    {"item": "Лимон", "amount": "1 шт"},
                    {"item": "Оливковое масло", "amount": "2 ст.л."},
                    {"item": "Соль, перец", "amount": "по вкусу"},
                    {"item": "Свежая зелень", "amount": "по вкусу"}
                ],
                "instructions": [
                    "Разогрейте духовку до 180°C",
                    "Рыбу промойте, обсушите, посолите и поперчите",
                    "Сбрызните оливковым маслом и лимонным соком",
                    "Заверните в фольгу или выложите на противень",
                    "Запекайте 20-25 минут",
                    "Подавайте с зеленью и овощным салатом"
                ],
                "nutrition": {
                    "kcal": 250,
                    "protein": 30,
                    "fat": 12,
                    "carbs": 5
                }
            }
        elif "омлет" in dish_lower or "яйц" in dish_lower:
            return {
                "name": dish_name,
                "description": "Быстрый и питательный завтрак",
                "servings": 1,
                "cooking_time": 10,
                "ingredients": [
                    {"item": "Яйца", "amount": "3 шт"},
                    {"item": "Молоко", "amount": "50 мл"},
                    {"item": "Болгарский перец", "amount": "50 г"},
                    {"item": "Помидоры", "amount": "50 г"},
                    {"item": "Сливочное масло", "amount": "10 г"},
                    {"item": "Соль, перец", "amount": "по вкусу"}
                ],
                "instructions": [
                    "Взбейте яйца с молоком, посолите, поперчите",
                    "Овощи нарежьте мелкими кубиками",
                    "Разогрейте сковороду с маслом",
                    "Обжарьте овощи 2-3 минуты",
                    "Залейте яичной смесью",
                    "Готовьте под крышкой на среднем огне 5-7 минут"
                ],
                "nutrition": {
                    "kcal": 280,
                    "protein": 20,
                    "fat": 15,
                    "carbs": 10
                }
            }
        elif "овсян" in dish_lower or "каш" in dish_lower:
            return {
                "name": dish_name,
                "description": "Классический здоровый завтрак",
                "servings": 1,
                "cooking_time": 10,
                "ingredients": [
                    {"item": "Овсяные хлопья", "amount": "60 г"},
                    {"item": "Молоко или вода", "amount": "200 мл"},
                    {"item": "Банан", "amount": "1 шт"},
                    {"item": "Мед", "amount": "1 ч.л."},
                    {"item": "Орехи", "amount": "20 г"}
                ],
                "instructions": [
                    "Залейте хлопья горячим молоком или водой",
                    "Варите 5-7 минут, помешивая",
                    "Добавьте нарезанный банан",
                    "Полейте медом, посыпьте орехами",
                    "Дайте настояться 2-3 минуты"
                ],
                "nutrition": {
                    "kcal": 350,
                    "protein": 12,
                    "fat": 8,
                    "carbs": 55
                }
            }
        elif "курица" in dish_lower or "грудка" in dish_lower:
            return {
                "name": dish_name,
                "description": "Диетическое белковое блюдо",
                "servings": 2,
                "cooking_time": 40,
                "ingredients": [
                    {"item": "Куриная грудка", "amount": "400 г"},
                    {"item": "Гречка", "amount": "150 г"},
                    {"item": "Соевый соус", "amount": "2 ст.л."},
                    {"item": "Чеснок", "amount": "2 зубчика"},
                    {"item": "Специи", "amount": "по вкусу"}
                ],
                "instructions": [
                    "Курицу нарежьте, замаринуйте в соевом соусе на 15 минут",
                    "Гречку промойте и отварите (1:2 с водой)",
                    "Обжарьте курицу с чесноком до готовности",
                    "Подавайте с гречкой и овощами"
                ],
                "nutrition": {
                    "kcal": 450,
                    "protein": 40,
                    "fat": 10,
                    "carbs": 50
                }
            }
        else:
            # Generic fallback
            return {
                "name": dish_name,
                "description": f"Рецепт для '{dish_name}' временно недоступен. Попробуйте выбрать другое блюдо или обратитесь к администратору для настройки AI.",
                "servings": 1,
                "cooking_time": 30,
                "ingredients": [
                    {"item": "Основные ингредиенты", "amount": "по рецепту"}
                ],
                "instructions": [
                    "💡 Рецепт находится в разработке",
                    "🔧 Настройте AI провайдер (Ollama или Gemini) для автоматической генерации",
                    "📧 Или обратитесь к администратору бота"
                ],
                "nutrition": {
                    "kcal": 0,
                    "protein": 0,
                    "fat": 0,
                    "carbs": 0
                }
            }
