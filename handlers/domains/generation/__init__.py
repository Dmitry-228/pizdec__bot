"""
Домен генерации контента.

Отвечает за:
- Генерацию фото по тексту
- Создание аватаров
- Генерацию видео
- Обработку изображений
- Управление стилями и промптами
"""

from .handlers import GenerationDomainHandler
from .callbacks import StyleCallbackHandler, GenerationCallbackHandler
from .messages import PromptMessageHandler, ImageMessageHandler
from .services import GenerationService, StyleService

__all__ = [
    'GenerationDomainHandler',
    'StyleCallbackHandler',
    'GenerationCallbackHandler',
    'PromptMessageHandler', 
    'ImageMessageHandler',
    'GenerationService',
    'StyleService'
]