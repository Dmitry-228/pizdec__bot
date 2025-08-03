"""
Сервисы для генерации контента.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from database import get_active_trainedmodel, update_user_balance
from generation.images import generate_image
from generation.videos import generate_video
from ..common.exceptions import GenerationError, ResourceError, ValidationError
from ..common.types import GenerationRequest

logger = logging.getLogger(__name__)


class GenerationService:
    """Сервис для генерации контента."""
    
    def __init__(self):
        self.style_service = StyleService()
    
    async def generate_photo(self, request: GenerationRequest) -> Dict[str, Any]:
        """Генерирует фото по запросу."""
        try:
            # Валидация запроса
            self._validate_generation_request(request, 'photo')
            
            # Проверяем ресурсы пользователя
            await self._check_user_resources(request.user_id, photos=1)
            
            # Подготавливаем параметры генерации
            generation_params = await self._prepare_photo_params(request)
            
            # Выполняем генерацию
            result = await self._execute_photo_generation(generation_params)
            
            # Списываем ресурсы
            await update_user_balance(request.user_id, "decrement_photo", 1)
            
            logger.info(f"Фото сгенерировано для user_id={request.user_id}, "
                       f"type={request.generation_type}, style={request.style}")
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка генерации фото для user_id={request.user_id}: {e}", exc_info=True)
            raise GenerationError(f"Не удалось сгенерировать фото: {e}")
    
    async def generate_video(self, request: GenerationRequest) -> Dict[str, Any]:
        """Генерирует видео по запросу."""
        try:
            # Валидация запроса
            self._validate_generation_request(request, 'video')
            
            # Проверяем ресурсы пользователя
            await self._check_user_resources(request.user_id, photos=1)  # Видео тоже тратит печеньки
            
            # Подготавливаем параметры генерации
            generation_params = await self._prepare_video_params(request)
            
            # Выполняем генерацию
            result = await self._execute_video_generation(generation_params)
            
            # Списываем ресурсы
            await update_user_balance(request.user_id, "decrement_photo", 1)
            
            logger.info(f"Видео сгенерировано для user_id={request.user_id}, "
                       f"style={request.style}")
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка генерации видео для user_id={request.user_id}: {e}", exc_info=True)
            raise GenerationError(f"Не удалось сгенерировать видео: {e}")
    
    async def create_avatar(self, request: GenerationRequest) -> Dict[str, Any]:
        """Создает аватар пользователя."""
        try:
            # Валидация запроса
            self._validate_generation_request(request, 'avatar')
            
            # Проверяем ресурсы пользователя
            await self._check_user_resources(request.user_id, avatars=1)
            
            # Подготавливаем параметры создания аватара
            avatar_params = await self._prepare_avatar_params(request)
            
            # Выполняем создание аватара
            result = await self._execute_avatar_creation(avatar_params)
            
            # Списываем ресурсы
            await update_user_balance(request.user_id, "decrement_avatar", 1)
            
            logger.info(f"Аватар создан для user_id={request.user_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка создания аватара для user_id={request.user_id}: {e}", exc_info=True)
            raise GenerationError(f"Не удалось создать аватар: {e}")
    
    def _validate_generation_request(self, request: GenerationRequest, expected_type: str):
        """Валидирует запрос на генерацию."""
        if request.generation_type != expected_type:
            raise ValidationError(f"Неверный тип генерации: ожидался {expected_type}, получен {request.generation_type}")
        
        if expected_type in ['photo', 'video'] and not request.prompt:
            raise ValidationError("Промпт обязателен для генерации фото/видео")
        
        if expected_type == 'avatar' and not request.face_image_path:
            raise ValidationError("Изображение лица обязательно для создания аватара")
    
    async def _check_user_resources(self, user_id: int, photos: int = 0, avatars: int = 0):
        """Проверяет достаточность ресурсов пользователя."""
        from database import check_database_user
        
        user_data = await check_database_user(user_id)
        if not user_data:
            raise ValidationError("Пользователь не найден")
        
        generations_left = user_data[0] if user_data[0] is not None else 0
        avatar_left = user_data[1] if user_data[1] is not None else 0
        
        if photos > 0 and generations_left < photos:
            raise ResourceError(f"Недостаточно печенек! Нужно: {photos}, у вас: {generations_left}", "photos")
        
        if avatars > 0 and avatar_left < avatars:
            raise ResourceError(f"Недостаточно аватаров! Нужно: {avatars}, у вас: {avatar_left}", "avatars")
    
    async def _prepare_photo_params(self, request: GenerationRequest) -> Dict[str, Any]:
        """Подготавливает параметры для генерации фото."""
        params = {
            'user_id': request.user_id,
            'prompt': request.prompt,
            'style': request.style or 'default',
            'model_key': request.model_key or 'flux-trained',
            'aspect_ratio': request.aspect_ratio or '1:1',
            'generation_type': request.generation_type
        }
        
        # Добавляем изображение лица, если есть
        if request.face_image_path:
            params['face_image_path'] = request.face_image_path
            params['generation_type'] = 'with_avatar'
        
        # Добавляем дополнительные параметры
        if request.additional_params:
            params.update(request.additional_params)
        
        return params
    
    async def _prepare_video_params(self, request: GenerationRequest) -> Dict[str, Any]:
        """Подготавливает параметры для генерации видео."""
        params = {
            'user_id': request.user_id,
            'prompt': request.prompt,
            'style': request.style or 'default',
            'duration': 3,  # Стандартная длительность видео
        }
        
        # Добавляем изображение лица, если есть
        if request.face_image_path:
            params['face_image_path'] = request.face_image_path
        
        # Добавляем дополнительные параметры
        if request.additional_params:
            params.update(request.additional_params)
        
        return params
    
    async def _prepare_avatar_params(self, request: GenerationRequest) -> Dict[str, Any]:
        """Подготавливает параметры для создания аватара."""
        params = {
            'user_id': request.user_id,
            'face_image_path': request.face_image_path,
            'avatar_name': request.additional_params.get('avatar_name', 'Мой аватар') if request.additional_params else 'Мой аватар'
        }
        
        return params
    
    async def _execute_photo_generation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Выполняет генерацию фото."""
        # Здесь вызывается существующая логика генерации
        # Это заглушка - в реальности нужно интегрировать с существующим кодом
        result = {
            'success': True,
            'image_urls': ['https://example.com/generated_image.jpg'],
            'generation_id': f"gen_{datetime.now().timestamp()}",
            'duration': 5.2,
            'model_used': params.get('model_key', 'flux-trained')
        }
        
        return result
    
    async def _execute_video_generation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Выполняет генерацию видео."""
        # Заглушка для генерации видео
        result = {
            'success': True,
            'video_url': 'https://example.com/generated_video.mp4',
            'generation_id': f"video_{datetime.now().timestamp()}",
            'duration': params.get('duration', 3)
        }
        
        return result
    
    async def _execute_avatar_creation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Выполняет создание аватара."""
        # Заглушка для создания аватара
        result = {
            'success': True,
            'avatar_id': f"avatar_{datetime.now().timestamp()}",
            'status': 'training',
            'estimated_time': 300  # 5 минут
        }
        
        return result


class StyleService:
    """Сервис для работы со стилями генерации."""
    
    def get_available_styles(self, generation_type: str = 'photo') -> Dict[str, Any]:
        """Получает доступные стили для типа генерации."""
        if generation_type == 'photo':
            return self._get_photo_styles()
        elif generation_type == 'video':
            return self._get_video_styles()
        elif generation_type == 'avatar':
            return self._get_avatar_styles()
        else:
            return {}
    
    def _get_photo_styles(self) -> Dict[str, Any]:
        """Получает стили для фото."""
        return {
            'realistic': {
                'name': 'Реалистичный',
                'description': 'Фотореалистичные изображения',
                'prompt_suffix': ', photorealistic, high quality, detailed'
            },
            'artistic': {
                'name': 'Художественный',
                'description': 'Художественный стиль',
                'prompt_suffix': ', artistic, creative, stylized'
            },
            'anime': {
                'name': 'Аниме',
                'description': 'Стиль аниме',
                'prompt_suffix': ', anime style, manga, japanese art'
            },
            'portrait': {
                'name': 'Портрет',
                'description': 'Портретная съемка',
                'prompt_suffix': ', portrait, professional photography, studio lighting'
            }
        }
    
    def _get_video_styles(self) -> Dict[str, Any]:
        """Получает стили для видео."""
        return {
            'cinematic': {
                'name': 'Кинематографический',
                'description': 'Кинематографический стиль',
                'prompt_suffix': ', cinematic, movie style, dramatic lighting'
            },
            'smooth': {
                'name': 'Плавный',
                'description': 'Плавные движения',
                'prompt_suffix': ', smooth motion, fluid animation'
            }
        }
    
    def _get_avatar_styles(self) -> Dict[str, Any]:
        """Получает стили для аватаров."""
        return {
            'professional': {
                'name': 'Профессиональный',
                'description': 'Деловой стиль'
            },
            'casual': {
                'name': 'Повседневный',
                'description': 'Повседневный стиль'
            },
            'artistic': {
                'name': 'Художественный',
                'description': 'Творческий стиль'
            }
        }
    
    def get_style_prompt(self, style_key: str, generation_type: str = 'photo') -> str:
        """Получает промпт для стиля."""
        styles = self.get_available_styles(generation_type)
        style = styles.get(style_key, {})
        return style.get('prompt_suffix', '')
    
    def validate_style(self, style_key: str, generation_type: str = 'photo') -> bool:
        """Проверяет существование стиля."""
        styles = self.get_available_styles(generation_type)
        return style_key in styles