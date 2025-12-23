"""
Google Gemini AI provider for text generation
"""
import aiohttp
import logging
from typing import Optional
from bot.config import settings

logger = logging.getLogger(__name__)


class GeminiProvider:
    """Google Gemini text generation provider"""
    
    def __init__(self, model: str = "gemini-2.0-flash-exp"):
        self.model = model
        self.api_key = settings.GEMINI_API_KEY
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not set in environment")
    
    async def generate_text(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2048) -> str:
        """Generate text response from prompt"""
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not configured")
        
        url = f"{self.base_url}?key={self.api_key}"
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "topP": 0.95,
                "topK": 40
            }
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Gemini API error: {response.status} - {error_text}")
                        raise Exception(f"Gemini API returned {response.status}")
                    
                    data = await response.json()
                    
                    # Extract text from response
                    if "candidates" in data and len(data["candidates"]) > 0:
                        candidate = data["candidates"][0]
                        if "content" in candidate and "parts" in candidate["content"]:
                            parts = candidate["content"]["parts"]
                            if len(parts) > 0 and "text" in parts[0]:
                                return parts[0]["text"]
                    
                    logger.error(f"Unexpected Gemini response format: {data}")
                    raise Exception("Failed to extract text from Gemini response")
                    
        except aiohttp.ClientError as e:
            logger.error(f"Network error calling Gemini: {e}")
            raise Exception(f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Error generating text with Gemini: {e}")
            raise
