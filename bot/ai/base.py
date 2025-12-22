"""
Base AI provider interface
Abstraction for different AI services (Ollama, Gemini, OpenAI, etc.)
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class FoodItem:
    """Single food item with nutrition"""
    name: str
    calories: float
    protein: float  # grams
    fat: float      # grams
    carbs: float    # grams
    confidence: float = 0.8  # 0.0 to 1.0


@dataclass
class FoodEstimate:
    """Complete food estimate result"""
    items: List[FoodItem]
    total_calories: float
    total_protein: float
    total_fat: float
    total_carbs: float
    raw_response: str
    model_used: str
    confidence: float = 0.8


class AIProvider(ABC):
    """Abstract base class for AI providers"""
    
    @abstractmethod
    async def estimate_food(self, food_text: str, language: str = "ru") -> Optional[FoodEstimate]:
        """
        Estimate calories and macros from food description
        
        Args:
            food_text: Description of food items
            language: Language of the text (ru/en)
        
        Returns:
            FoodEstimate or None if failed
        """
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if AI service is available"""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get provider name"""
        pass
