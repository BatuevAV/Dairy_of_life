"""
Abstract base class for Vision AI providers (photo food recognition)
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ClarificationQuestion:
    """Уточняющий вопрос для пользователя"""
    question: str  # Текст вопроса
    options: List[str]  # Варианты ответов
    field: str  # Поле, которое уточняется (sauce, portion, etc)


@dataclass
class PhotoFoodEstimate:
    """Результат анализа фото еды"""
    # Что видит AI
    detected_items: List[str]  # ["паста с курицей", "соус сливочный"]
    description: str  # Полное описание увиденного
    
    # Оценка
    calories: float
    protein: float
    fat: float
    carbs: float
    
    # Метаданные
    confidence: float  # 0.0 - 1.0
    confidence_level: str  # "low", "medium", "high"
    
    # Уточнения
    clarification_questions: List[ClarificationQuestion]
    assumptions: List[str]  # Предположения, которые сделал AI
    
    # Технические данные
    model_used: str
    raw_response: str


class VisionAIProvider(ABC):
    """Абстрактный провайдер для анализа фото еды"""
    
    @abstractmethod
    async def analyze_food_photo(
        self,
        photo_bytes: bytes,
        additional_context: Optional[str] = None
    ) -> Optional[PhotoFoodEstimate]:
        """
        Анализировать фото еды и вернуть оценку калорий
        
        Args:
            photo_bytes: Байты изображения
            additional_context: Дополнительный контекст (ответы на вопросы)
        
        Returns:
            PhotoFoodEstimate или None если не удалось распознать
        """
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Проверить доступность сервиса"""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Получить имя провайдера"""
        pass
    
    @abstractmethod
    def requires_api_key(self) -> bool:
        """Требуется ли API ключ"""
        pass
