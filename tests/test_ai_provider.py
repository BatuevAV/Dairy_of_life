"""
Тесты для AI provider (Ollama)
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from bot.ai.ollama_provider import OllamaProvider
from bot.ai.base import FoodItem, FoodEstimate


class TestOllamaProvider:
    """Тесты для Ollama AI provider"""
    
    @pytest.fixture
    def provider(self):
        return OllamaProvider(
            host="http://localhost:11434",
            model="llama3.2"
        )
    
    def test_build_prompt(self, provider):
        """Тест генерации промпта"""
        description = "Сэндвич из Starbucks, macaron, чай"
        prompt = provider._build_prompt(description)
        
        assert "Starbucks" in prompt
        assert "macaron" in prompt
        assert "чай" in prompt
        assert "JSON" in prompt
        assert "calories" in prompt
    
    def test_parse_response_valid_json(self, provider):
        """Тест парсинга валидного JSON ответа"""
        response = """
        Here is the estimate:
        
        ```json
        {
            "items": [
                {
                    "name": "Multigrain sandwich",
                    "calories": 450,
                    "protein": 25,
                    "fat": 15,
                    "carbs": 45
                },
                {
                    "name": "Macaron",
                    "calories": 140,
                    "protein": 2,
                    "fat": 6,
                    "carbs": 20
                }
            ],
            "confidence": 0.75
        }
        ```
        """
        
        result = provider._parse_response(response)
        
        assert result is not None
        assert len(result.items) == 2
        assert result.items[0].name == "Multigrain sandwich"
        assert result.items[0].calories == 450
        assert result.items[1].name == "Macaron"
        assert result.confidence == 0.75
    
    def test_parse_response_without_json_markers(self, provider):
        """Тест парсинга JSON без маркеров"""
        response = """
        {
            "items": [
                {"name": "Apple", "calories": 52, "protein": 0, "fat": 0, "carbs": 14}
            ],
            "confidence": 0.9
        }
        """
        
        result = provider._parse_response(response)
        
        assert result is not None
        assert len(result.items) == 1
        assert result.items[0].name == "Apple"
        assert result.confidence == 0.9
    
    def test_parse_response_invalid_json(self, provider):
        """Тест парсинга невалидного JSON"""
        response = "This is not a valid JSON response"
        
        result = provider._parse_response(response)
        
        assert result is None
    
    def test_parse_response_missing_fields(self, provider):
        """Тест парсинга JSON с отсутствующими полями"""
        response = """
        {
            "items": [
                {"name": "Sandwich", "calories": 400}
            ]
        }
        """
        
        result = provider._parse_response(response)
        
        assert result is not None
        assert len(result.items) == 1
        # Проверяем значения по умолчанию
        assert result.items[0].protein == 0
        assert result.items[0].fat == 0
        assert result.items[0].carbs == 0
        assert result.confidence == 0.5  # Значение по умолчанию
    
    @pytest.mark.asyncio
    async def test_estimate_food_success(self, provider):
        """Тест успешной оценки еды"""
        mock_response = {
            "response": """
            {
                "items": [
                    {"name": "Sandwich", "calories": 450, "protein": 25, "fat": 15, "carbs": 45}
                ],
                "confidence": 0.8
            }
            """
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            
            result = await provider.estimate_food("Sandwich from Starbucks")
            
            assert result is not None
            assert len(result.items) == 1
            assert result.items[0].name == "Sandwich"
            assert result.items[0].calories == 450
    
    @pytest.mark.asyncio
    async def test_estimate_food_empty_description(self, provider):
        """Тест с пустым описанием"""
        result = await provider.estimate_food("")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_is_available_success(self, provider):
        """Тест проверки доступности Ollama"""
        mock_response = {"models": [{"name": "llama3.2"}]}
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response)
            
            is_available = await provider.is_available()
            assert is_available is True
    
    @pytest.mark.asyncio
    async def test_is_available_failure(self, provider):
        """Тест недоступности Ollama"""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = Exception("Connection refused")
            
            is_available = await provider.is_available()
            assert is_available is False
    
    def test_get_provider_name(self, provider):
        """Тест получения имени провайдера"""
        name = provider.get_provider_name()
        assert name == "Ollama (llama3.2)"
    
    def test_calculate_totals(self, provider):
        """Тест расчета итоговых значений"""
        items = [
            FoodItem(name="Item1", calories=400, protein=20, fat=15, carbs=40),
            FoodItem(name="Item2", calories=200, protein=10, fat=5, carbs=30)
        ]
        
        total_kcal, total_protein, total_fat, total_carbs = provider._calculate_totals(items)
        
        assert total_kcal == 600
        assert total_protein == 30
        assert total_fat == 20
        assert total_carbs == 70
