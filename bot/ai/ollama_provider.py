"""
Ollama AI provider
Local AI for food calorie estimation
"""
import json
import logging
import re
from typing import Optional
import aiohttp

from bot.ai.base import AIProvider, FoodEstimate, FoodItem

logger = logging.getLogger(__name__)


class OllamaProvider(AIProvider):
    """Ollama local AI provider"""
    
    def __init__(self, host: str = "http://localhost:11434", model: str = "llama3.2"):
        self.host = host
        self.model = model
        self.timeout = 30
    
    async def is_available(self) -> bool:
        """Check if Ollama is running"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.host}/api/tags", timeout=aiohttp.ClientTimeout(total=5)) as response:
                    return response.status == 200
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            return False
    
    def get_provider_name(self) -> str:
        return f"Ollama ({self.model})"
    
    async def estimate_food(self, food_text: str, language: str = "ru") -> Optional[FoodEstimate]:
        """Estimate food calories using Ollama"""
        
        if not await self.is_available():
            logger.error("Ollama is not available")
            return None
        
        # Build prompt
        prompt = self._build_prompt(food_text, language)
        
        try:
            # Call Ollama API
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Very low = more consistent and deterministic
                        "num_predict": 500
                    }
                }
                
                async with session.post(
                    f"{self.host}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status != 200:
                        logger.error(f"Ollama API error: {response.status}")
                        return None
                    
                    result = await response.json()
                    ai_response = result.get("response", "")
                    
                    # Parse response
                    return self._parse_response(ai_response, food_text)
        
        except Exception as e:
            logger.error(f"Ollama estimation error: {e}")
            return None
    
    def _build_prompt(self, food_text: str, language: str) -> str:
        """Build prompt for Ollama"""
        
        if language == "ru":
            prompt = f"""Ты - эксперт по питанию. Оцени калорийность и БЖУ для блюда.

ВАЖНО: 
- Если в описании указан размер порции (кусочек, половина, полпорции) - используй его для расчета
- Кусочек = примерно 1/8 от стандартной порции
- Половина/полпорции = 50% от стандартной порции
- Стандартная порция = ~200-300г
- ОБЯЗАТЕЛЬНО пиши названия блюд по-русски ПОЛНОСТЬЮ без сокращений
- НЕ искажай русские слова - пиши их правильно

Примеры правильных оценок:
1. "Жареная рыба (филе) с картофелем фри":
   - Жареная рыба (филе): 250 ккал, 30г белка, 12г жира, 5г углеводов
   - Картофель фри: 350 ккал, 4г белка, 17г жира, 45г углеводов

2. "Салат из свежих овощей":
   - Салат из свежих овощей: 80 ккал, 3г белка, 2г жира, 15г углеводов

3. "Курица с гречкой":
   - Курица с гречкой: 400 ккал, 40г белка, 8г жира, 45г углеводов

4. "Кусочек торта" (обрати внимание - КУСОЧЕК, не целый торт!):
   - Кусочек торта: 320 ккал, 4г белка, 15г жира, 42г углеводов

Ответь ТОЛЬКО в формате JSON без дополнительного текста:

{{
  "items": [
    {{"name": "полное название блюда по-русски", "calories": число, "protein": число, "fat": число, "carbs": число}}
  ]
}}

Еда: {food_text}

JSON:"""
        else:
            prompt = f"""You are a nutrition expert. Estimate calories and macros for the food.

IMPORTANT:
- Use standard portions (1 serving = ~200-300g)
- Subway 30cm sandwich = ~400-500 kcal (depends on filling)
- Multigrain = whole grain bread
- Chicken Ham = chicken ham
- 3 Cheese = 3 types of cheese

Examples:
- Subway Multigrain Chicken Ham and 3 Cheese (30cm): ~450 kcal, 35g protein, 15g fat, 50g carbs
- Chicken with buckwheat: ~400 kcal, 40g protein, 8g fat, 45g carbs

Answer ONLY in JSON format without additional text:

{{
  "items": [
    {{"name": "food name", "calories": number, "protein": number, "fat": number, "carbs": number}}
  ]
}}

Food: {food_text}

JSON:"""
        
        return prompt
    
    def _parse_response(self, ai_response: str, original_text: str) -> Optional[FoodEstimate]:
        """Parse AI response to FoodEstimate"""
        
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if not json_match:
                logger.warning("No JSON found in Ollama response")
                return None
            
            json_str = json_match.group()
            data = json.loads(json_str)
            
            # Parse items
            items = []
            for item_data in data.get("items", []):
                try:
                    protein = float(item_data.get("protein", 0))
                    fat = float(item_data.get("fat", 0))
                    carbs = float(item_data.get("carbs", 0))
                    calories = float(item_data.get("calories", 0))
                    
                    # If calories is 0 but we have macros, calculate from macros
                    if calories == 0 and (protein > 0 or fat > 0 or carbs > 0):
                        calories = (protein * 4) + (fat * 9) + (carbs * 4)
                        logger.info(f"Recalculated calories from macros: {calories}")
                    
                    item = FoodItem(
                        name=item_data.get("name", "Unknown"),
                        calories=calories,
                        protein=protein,
                        fat=fat,
                        carbs=carbs,
                        confidence=0.75  # Ollama confidence
                    )
                    items.append(item)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Failed to parse item: {e}")
                    continue
            
            if not items:
                logger.warning("No valid items parsed")
                return None
            
            # Calculate totals
            total_calories = sum(item.calories for item in items)
            total_protein = sum(item.protein for item in items)
            total_fat = sum(item.fat for item in items)
            total_carbs = sum(item.carbs for item in items)
            
            return FoodEstimate(
                items=items,
                total_calories=total_calories,
                total_protein=total_protein,
                total_fat=total_fat,
                total_carbs=total_carbs,
                raw_response=ai_response,
                model_used=self.model,
                confidence=0.75
            )
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            logger.debug(f"Response was: {ai_response}")
            return None
        except Exception as e:
            logger.error(f"Parse error: {e}")
            return None
