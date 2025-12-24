"""
Smart AI Provider with automatic fallback
Tries Gemini first, falls back to Ollama if unavailable
"""
import logging
from typing import Optional
from bot.ai.gemini_provider import GeminiProvider
from bot.ai.ollama_provider import OllamaProvider
from bot.ai.base import AIProvider, FoodEstimate

logger = logging.getLogger(__name__)


class SmartAIProvider(AIProvider):
    """
    Smart AI provider that automatically switches between Gemini and Ollama.
    
    Priority:
    1. Try Gemini (fast, cloud-based)
    2. Fallback to Ollama (local, always available)
    """
    
    def __init__(self):
        self.gemini = GeminiProvider()
        self.ollama = OllamaProvider()
        self._last_gemini_failed = False
        self._gemini_consecutive_failures = 0
        
    def get_provider_name(self) -> str:
        return "SmartAI (Gemini → Ollama)"
    
    async def is_available(self) -> bool:
        """Check if at least one provider is available"""
        # Try Gemini first
        try:
            from bot.config import settings
            if settings.GEMINI_API_KEY:
                return True
        except:
            pass
        
        # Check Ollama as fallback
        try:
            return await self.ollama.is_available()
        except:
            return False
    
    async def _try_gemini(self) -> bool:
        """Check if Gemini is available (quick test)"""
        # If Gemini failed multiple times, skip check for a while
        if self._gemini_consecutive_failures > 3:
            logger.info("Gemini has multiple failures, using Ollama directly")
            return False
            
        try:
            # Quick test with timeout
            from bot.config import settings
            if not settings.GEMINI_API_KEY:
                return False
            return True
        except Exception as e:
            logger.warning(f"Gemini availability check failed: {e}")
            return False
    
    async def estimate_food(self, food_text: str, language: str = "ru") -> Optional[FoodEstimate]:
        """Estimate food with automatic fallback"""
        
        # Try Gemini first
        if await self._try_gemini():
            try:
                logger.info("Trying Gemini for food estimation")
                result = await self._estimate_with_gemini(food_text, language)
                if result:
                    self._gemini_consecutive_failures = 0
                    self._last_gemini_failed = False
                    logger.info("✅ Gemini succeeded")
                    return result
            except Exception as e:
                error_str = str(e)
                self._gemini_consecutive_failures += 1
                
                # Check if it's a quota/rate limit error
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    logger.warning("🚫 Gemini quota exhausted (429), switching to Ollama")
                    self._last_gemini_failed = True
                elif "401" in error_str or "UNAUTHENTICATED" in error_str:
                    logger.error("🔐 Gemini authentication failed")
                    self._last_gemini_failed = True
                else:
                    logger.warning(f"Gemini error: {e}, trying Ollama")
        
        # Fallback to Ollama
        logger.info("Using Ollama as fallback")
        try:
            if not await self.ollama.is_available():
                logger.error("❌ Ollama is not available")
                return None
            
            result = await self.ollama.estimate_food(food_text, language)
            if result:
                logger.info("✅ Ollama succeeded")
            return result
        except Exception as e:
            logger.error(f"Ollama also failed: {e}")
            return None
    
    async def _estimate_with_gemini(self, food_text: str, language: str) -> Optional[FoodEstimate]:
        """Estimate food using Gemini (with prompt similar to Ollama)"""
        
        prompt = f"""Проанализируй описание еды и оцени калорийность и БЖУ.

Еда: {food_text}

Инструкции:
1. Определи все блюда/продукты
2. Оцени порции (граммы)
3. Рассчитай калории и БЖУ для КАЖДОГО продукта
4. Суммируй итого

Примеры оценки:
- Сэндвич Subway (30см): ~450 ккал, 25г белка, 12г жира, 60г углеводов
- Яблоко среднее: ~80 ккал, 0.5г белка, 0г жира, 21г углеводов
- Омлет из 2 яиц: ~180 ккал, 12г белка, 14г жира, 2г углеводов

Ответ СТРОГО в JSON:
{{
  "items": [
    {{
      "name": "название блюда",
      "portion": "вес в граммах",
      "calories": калории_число,
      "protein": белки_число,
      "fat": жиры_число,
      "carbs": углеводы_число
    }}
  ],
  "total_calories": общие_калории,
  "total_protein": общие_белки,
  "total_fat": общие_жиры,
  "total_carbs": общие_углеводы
}}

Будь точным в оценках! Не занижай калорийность."""

        try:
            response = await self.gemini.generate_text(prompt, temperature=0.1)
            
            # Parse JSON response
            import json
            import re
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                logger.error("No JSON found in Gemini response")
                return None
            
            data = json.loads(json_match.group())
            
            # Convert to FoodEstimate
            from bot.ai.base import FoodItem
            
            items = []
            for item_data in data.get("items", []):
                item = FoodItem(
                    name=item_data.get("name", ""),
                    portion=item_data.get("portion", ""),
                    calories=float(item_data.get("calories", 0)),
                    protein=float(item_data.get("protein", 0)),
                    fat=float(item_data.get("fat", 0)),
                    carbs=float(item_data.get("carbs", 0))
                )
                items.append(item)
            
            estimate = FoodEstimate(
                items=items,
                total_calories=float(data.get("total_calories", 0)),
                total_protein=float(data.get("total_protein", 0)),
                total_fat=float(data.get("total_fat", 0)),
                total_carbs=float(data.get("total_carbs", 0)),
                ai_provider="Gemini"
            )
            
            return estimate
            
        except Exception as e:
            logger.error(f"Gemini estimation failed: {e}")
            raise
    
    async def generate_text(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2048) -> str:
        """
        Generate text with automatic fallback.
        Tries Gemini first, falls back to Ollama.
        """
        
        # Try Gemini first
        if await self._try_gemini():
            try:
                logger.info("Trying Gemini for text generation")
                result = await self.gemini.generate_text(prompt, temperature, max_tokens)
                if result:
                    self._gemini_consecutive_failures = 0
                    self._last_gemini_failed = False
                    logger.info("✅ Gemini text generation succeeded")
                    return result
            except Exception as e:
                error_str = str(e)
                self._gemini_consecutive_failures += 1
                
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    logger.warning("🚫 Gemini quota exhausted, switching to Ollama")
                    self._last_gemini_failed = True
                else:
                    logger.warning(f"Gemini error: {e}, trying Ollama")
        
        # Fallback to Ollama
        logger.info("Using Ollama for text generation")
        try:
            if not await self.ollama.is_available():
                logger.error("❌ Ollama is not available")
                raise Exception("Ollama is not available")
            
            # Ollama doesn't have direct generate_text, use API directly
            import aiohttp
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.ollama.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                }
                
                async with session.post(
                    f"{self.ollama.host}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status != 200:
                        raise Exception(f"Ollama API error: {response.status}")
                    
                    data = await response.json()
                    result = data.get("response", "")
                    
                    if not result:
                        raise Exception("Empty response from Ollama")
                    
                    logger.info("✅ Ollama text generation succeeded")
                    return result
                    
        except Exception as e:
            logger.error(f"Ollama text generation failed: {e}")
            raise
