"""AI module for food calorie estimation"""
from bot.ai.base import AIProvider, FoodEstimate
from bot.ai.ollama_provider import OllamaProvider

__all__ = ['AIProvider', 'FoodEstimate', 'OllamaProvider']
