"""
Gemini Vision AI provider for food photo recognition
Free tier: 15 requests per minute, 1500 per day
"""
import json
import logging
from typing import Optional
import aiohttp

from bot.ai.vision_base import (
    VisionAIProvider,
    PhotoFoodEstimate,
    ClarificationQuestion
)

logger = logging.getLogger(__name__)


class GeminiVisionProvider(VisionAIProvider):
    """Google Gemini Vision для анализа фото еды"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.5-flash"
    ):
        self.api_key = api_key
        self.model = model
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    
    def _build_prompt(self, additional_context: Optional[str] = None) -> str:
        """Построить промпт для анализа фото"""
        base_prompt = """Ты - эксперт по питанию. Проанализируй фото еды и дай оценку калорийности.

КРИТИЧЕСКИ ВАЖНО: 
1. Отвечай ТОЛЬКО валидным JSON
2. НЕ используй markdown блоки (```json или ```)
3. Все строки должны быть правильно закрыты кавычками
4. НЕ используй переносы строк внутри значений

Формат ответа (СТРОГО JSON):

{
  "detected_items": ["блюдо 1", "блюдо 2"],
  "description": "краткое описание одной строкой",
  "calories": 800,
  "protein": 40,
  "fat": 30,
  "carbs": 85,
  "confidence": 0.75,
  "confidence_level": "medium",
  "clarification_questions": [
    {
      "question": "Соус какой?",
      "options": ["сливочный", "томатный", "без соуса"],
      "field": "sauce"
    }
  ],
  "assumptions": ["порция стандартная", "приготовлено на масле"]
}

Правила:
- detected_items: список блюд (2-4 элемента)
- description: одна строка, без переносов
- calories, protein, fat, carbs: только числа
- confidence: число от 0.0 до 1.0
- confidence_level: "low" или "medium" или "high"
- clarification_questions: максимум 2 вопроса, каждый с 2-3 вариантами
- assumptions: 2-3 предположения о порции/приготовлении

Примеры вопросов:
- "Это одна порция?" options: ["да", "пополам"]
- "Соус?" options: ["сливочный", "томатный", "нет"]
- "Добавляли сыр?" options: ["нет", "немного", "да"]

НАЧНИ ОТВЕТ С { И ЗАКОНЧИ }"""
        
        if additional_context:
            base_prompt += f"\n\nДоп. инфо: {additional_context}\nОбнови оценку."
        
        return base_prompt
    
    async def analyze_food_photo(
        self,
        photo_bytes: bytes,
        additional_context: Optional[str] = None
    ) -> Optional[PhotoFoodEstimate]:
        """Анализировать фото еды через Gemini Vision"""
        
        if not self.api_key:
            logger.error("Gemini API key не установлен")
            return None
        
        try:
            # Конвертируем bytes в base64
            import base64
            photo_base64 = base64.b64encode(photo_bytes).decode('utf-8')
            
            # Строим запрос (Gemini API format)
            payload = {
                "contents": [{
                    "parts": [
                        {"text": self._build_prompt(additional_context)},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": photo_base64
                            }
                        }
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.2,  # Меньше креативности для точности
                    "topK": 32,
                    "topP": 1,
                    "maxOutputTokens": 2048,
                    "responseMimeType": "application/json"  # Требуем JSON
                }
            }
            
            # Отправляем запрос
            async with aiohttp.ClientSession() as session:
                url = f"{self.api_url}?key={self.api_key}"
                headers = {
                    "Content-Type": "application/json"
                }
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Gemini API error: {response.status}, {error_text}")
                        return None
                    
                    result = await response.json()
            
            # Парсим ответ
            if not result.get('candidates'):
                logger.error("Gemini не вернул candidates")
                return None
            
            text_response = result['candidates'][0]['content']['parts'][0]['text']
            
            # Парсим JSON из ответа
            estimate = self._parse_response(text_response)
            
            if estimate:
                estimate.model_used = self.model
                estimate.raw_response = text_response
            
            return estimate
            
        except Exception as e:
            logger.error(f"Ошибка анализа фото через Gemini: {e}", exc_info=True)
            return None
    
    def _parse_response(self, text: str) -> Optional[PhotoFoodEstimate]:
        """Парсить JSON ответ от Gemini"""
        try:
            # Агрессивная очистка от markdown и мусора
            text = text.strip()
            
            # Удаляем markdown блоки
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                # Может быть просто ``` без json
                parts = text.split('```')
                for part in parts:
                    part = part.strip()
                    if part.startswith('{') and part.endswith('}'):
                        text = part
                        break
            
            # Ищем JSON между { и }
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1:
                text = text[start:end+1]
            
            text = text.strip()
            
            # Попытка парсинга с обработкой переносов строк
            try:
                data = json.loads(text)
            except json.JSONDecodeError as e:
                # Если не получилось, пробуем очистить переносы строк внутри строк
                import re
                logger.warning(f"Первая попытка парсинга не удалась: {e}. Пробуем очистить JSON...")
                # Заменяем переносы строк внутри строковых значений на пробелы
                text = re.sub(r':\s*"([^"]*\n[^"]*)"', lambda m: ': "' + m.group(1).replace('\n', ' ') + '"', text, flags=re.MULTILINE)
                data = json.loads(text)
            
            # Парсим уточняющие вопросы
            questions = []
            for q in data.get('clarification_questions', []):
                try:
                    questions.append(ClarificationQuestion(
                        question=q.get('question', ''),
                        options=q.get('options', []),
                        field=q.get('field', 'general')
                    ))
                except:
                    continue
            
            return PhotoFoodEstimate(
                detected_items=data.get('detected_items', []),
                description=data.get('description', ''),
                calories=float(data.get('calories', 0)),
                protein=float(data.get('protein', 0)),
                fat=float(data.get('fat', 0)),
                carbs=float(data.get('carbs', 0)),
                confidence=float(data.get('confidence', 0.5)),
                confidence_level=data.get('confidence_level', 'medium'),
                clarification_questions=questions,
                assumptions=data.get('assumptions', []),
                model_used='',
                raw_response=''
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Не удалось распарсить JSON от Gemini: {e}")
            logger.debug(f"Ответ Gemini: {text[:500]}")
            
            # Fallback: попробуем извлечь данные regex
            return self._fallback_parse(text)
            
        except Exception as e:
            logger.error(f"Ошибка парсинга ответа Gemini: {e}")
            return None
    
    def _fallback_parse(self, text: str) -> Optional[PhotoFoodEstimate]:
        """Резервный парсинг если JSON невалидный"""
        import re
        
        try:
            # Извлекаем калории
            cal_match = re.search(r'"calories":\s*(\d+\.?\d*)', text)
            calories = float(cal_match.group(1)) if cal_match else 500.0
            
            # Извлекаем БЖУ
            protein_match = re.search(r'"protein":\s*(\d+\.?\d*)', text)
            protein = float(protein_match.group(1)) if protein_match else 30.0
            
            fat_match = re.search(r'"fat":\s*(\d+\.?\d*)', text)
            fat = float(fat_match.group(1)) if fat_match else 20.0
            
            carbs_match = re.search(r'"carbs":\s*(\d+\.?\d*)', text)
            carbs = float(carbs_match.group(1)) if carbs_match else 50.0
            
            # Извлекаем описание
            desc_match = re.search(r'"description":\s*"([^"]*)"', text)
            description = desc_match.group(1) if desc_match else "Еда на фото"
            
            logger.warning("Использован fallback парсинг - данные могут быть неточными")
            
            return PhotoFoodEstimate(
                detected_items=["Блюдо на фото"],
                description=description,
                calories=calories,
                protein=protein,
                fat=fat,
                carbs=carbs,
                confidence=0.3,
                confidence_level='low',
                clarification_questions=[],
                assumptions=["Оценка приблизительная (ошибка парсинга JSON)"],
                model_used='',
                raw_response=''
            )
        except Exception as e:
            logger.error(f"Fallback парсинг не удался: {e}")
            return None
    
    async def is_available(self) -> bool:
        """Проверить доступность Gemini API"""
        if not self.api_key:
            return False
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}?key={self.api_key}"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    return response.status == 200
        except Exception:
            return False
    
    def get_provider_name(self) -> str:
        """Получить имя провайдера"""
        return f"Google Gemini Vision ({self.model})"
    
    def requires_api_key(self) -> bool:
        """Требуется ли API ключ"""
        return True
