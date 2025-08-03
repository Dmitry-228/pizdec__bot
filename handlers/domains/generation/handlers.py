"""
Основные хендлеры домена генерации.
"""

from aiogram import Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from states import BotStates
from ..common.base import BaseDomainHandler
from ..common.decorators import log_handler_call
from ..common.types import HandlerResult, CallbackResult
from .callbacks import (
    GenerationMenuCallbackHandler, PhotoGenerationCallbackHandler,
    AvatarGenerationCallbackHandler, VideoGenerationCallbackHandler,
    StyleCallbackHandler, CreateAvatarCallbackHandler
)
from .messages import PromptMessageHandler, ImageMessageHandler
from .services import GenerationService, StyleService


class GenerationDomainHandler(BaseDomainHandler):
    """Основной хендлер домена генерации."""
    
    def __init__(self, bot: Bot):
        super().__init__(bot)
        self.generation_service = GenerationService()
        self.style_service = StyleService()
        self._register_handlers()
    
    def _register_handlers(self):
        """Регистрирует хендлеры домена."""
        # Callback хендлеры
        self.register_callback("generation_menu", GenerationMenuCallbackHandler(self.bot))
        self.register_callback("generate_photo", PhotoGenerationCallbackHandler(self.bot))
        self.register_callback("generate_avatar", AvatarGenerationCallbackHandler(self.bot))
        self.register_callback("generate_video", VideoGenerationCallbackHandler(self.bot))
        self.register_callback("create_avatar", CreateAvatarCallbackHandler(self.bot))
        self.register_callback("style_", StyleCallbackHandler(self.bot))
        
        # Message хендлеры по состояниям FSM
        self.register_message(BotStates.AWAITING_PROMPT, PromptMessageHandler(self.bot))
        self.register_message(BotStates.AWAITING_FACE_IMAGE, ImageMessageHandler(self.bot))
        self.register_message(BotStates.AWAITING_STYLE_SELECTION, PromptMessageHandler(self.bot))
    
    @log_handler_call
    async def handle_generation_menu(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Показывает меню генерации."""
        handler = self.callbacks.get("generation_menu")
        if handler:
            return await handler.process_callback(query, state)
        return CallbackResult.error_result("Handler not found")
    
    @log_handler_call
    async def handle_photo_generation(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Обрабатывает запрос на генерацию фото."""
        callback_data = query.data
        
        if callback_data == "generate_photo":
            handler = self.callbacks.get("generate_photo")
        elif callback_data == "generate_avatar":
            handler = self.callbacks.get("generate_avatar")
        elif callback_data == "generate_video":
            handler = self.callbacks.get("generate_video")
        elif callback_data == "create_avatar":
            handler = self.callbacks.get("create_avatar")
        elif callback_data.startswith("style_"):
            handler = self.callbacks.get("style_")
        else:
            return CallbackResult.error_result("Unknown generation callback")
        
        if handler:
            return await handler.process_callback(query, state)
        return CallbackResult.error_result("Handler not found")
    
    @log_handler_call
    async def handle_prompt_message(self, message: Message, state: FSMContext) -> HandlerResult:
        """Обрабатывает текстовые промпты."""
        current_state = await state.get_state()
        
        if current_state in [BotStates.AWAITING_PROMPT, BotStates.AWAITING_STYLE_SELECTION]:
            handler = self.messages.get(BotStates.AWAITING_PROMPT)
            if handler:
                return await handler.process_message(message, state)
        
        return HandlerResult.error_result("Invalid state for prompt input")
    
    @log_handler_call
    async def handle_image_message(self, message: Message, state: FSMContext) -> HandlerResult:
        """Обрабатывает загруженные изображения."""
        current_state = await state.get_state()
        
        if current_state == BotStates.AWAITING_FACE_IMAGE:
            handler = self.messages.get(BotStates.AWAITING_FACE_IMAGE)
            if handler:
                return await handler.process_message(message, state)
        
        return HandlerResult.error_result("Invalid state for image input")
    
    # Административные методы
    async def get_generation_statistics(self, start_date: str = None, end_date: str = None) -> dict:
        """Получает статистику генераций для администратора."""
        try:
            from database import get_generation_stats
            
            # Если даты не указаны, берем последние 30 дней
            if not start_date or not end_date:
                from datetime import datetime, timedelta
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
            stats = await get_generation_stats(start_date, end_date)
            
            return {
                'period': f"{start_date} - {end_date}",
                'total_generations': stats.get('total', 0),
                'photo_generations': stats.get('photos', 0),
                'video_generations': stats.get('videos', 0),
                'avatar_creations': stats.get('avatars', 0),
                'success_rate': stats.get('success_rate', 0),
                'average_duration': stats.get('avg_duration', 0)
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка получения статистики генераций: {e}", exc_info=True)
            return {}
    
    async def get_user_generations(self, user_id: int, limit: int = 10) -> list:
        """Получает историю генераций пользователя."""
        try:
            from database import get_user_generations
            
            generations = await get_user_generations(user_id, limit)
            
            # Форматируем данные для отображения
            formatted_generations = []
            for gen in generations:
                formatted_generations.append({
                    'id': gen[0],
                    'type': gen[1],
                    'style': gen[2] if len(gen) > 2 else 'unknown',
                    'status': gen[3] if len(gen) > 3 else 'unknown',
                    'created_at': gen[4] if len(gen) > 4 else None,
                    'duration': gen[5] if len(gen) > 5 else None
                })
            
            return formatted_generations
            
        except Exception as e:
            self.logger.error(f"Ошибка получения истории генераций для user_id={user_id}: {e}", exc_info=True)
            return []
    
    def get_available_styles(self, generation_type: str = 'photo') -> dict:
        """Получает доступные стили для типа генерации."""
        return self.style_service.get_available_styles(generation_type)
    
    async def admin_generate_for_user(
        self, 
        admin_id: int, 
        target_user_id: int, 
        generation_type: str,
        prompt: str = None,
        style: str = None
    ) -> dict:
        """Позволяет администратору сгенерировать контент для пользователя."""
        try:
            from ..common.types import GenerationRequest
            
            # Создаем запрос от имени пользователя
            request = GenerationRequest(
                user_id=target_user_id,
                generation_type=generation_type,
                prompt=prompt,
                style=style or 'realistic',
                additional_params={
                    'admin_generation': True,
                    'admin_id': admin_id
                }
            )
            
            # Выполняем генерацию без списания ресурсов
            if generation_type == 'photo':
                result = await self.generation_service.generate_photo(request)
            elif generation_type == 'video':
                result = await self.generation_service.generate_video(request)
            else:
                return {'success': False, 'error': 'Unsupported generation type'}
            
            self.logger.info(f"Админская генерация: admin_id={admin_id}, target_user_id={target_user_id}, type={generation_type}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка админской генерации: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    async def get_failed_generations(self, limit: int = 50) -> list:
        """Получает список неудачных генераций для анализа."""
        try:
            from database import get_failed_generations
            
            failed_gens = await get_failed_generations(limit)
            
            return [
                {
                    'id': gen[0],
                    'user_id': gen[1],
                    'type': gen[2],
                    'error': gen[3] if len(gen) > 3 else 'unknown',
                    'created_at': gen[4] if len(gen) > 4 else None
                }
                for gen in failed_gens
            ]
            
        except Exception as e:
            self.logger.error(f"Ошибка получения неудачных генераций: {e}", exc_info=True)
            return []
    
    async def retry_failed_generation(self, generation_id: int) -> bool:
        """Повторяет неудачную генерацию."""
        try:
            from database import get_generation_by_id, update_generation_status
            
            # Получаем данные генерации
            gen_data = await get_generation_by_id(generation_id)
            if not gen_data:
                return False
            
            # Создаем новый запрос
            request = GenerationRequest(
                user_id=gen_data['user_id'],
                generation_type=gen_data['type'],
                prompt=gen_data.get('prompt'),
                style=gen_data.get('style', 'realistic')
            )
            
            # Выполняем генерацию
            if gen_data['type'] == 'photo':
                result = await self.generation_service.generate_photo(request)
            elif gen_data['type'] == 'video':
                result = await self.generation_service.generate_video(request)
            else:
                return False
            
            # Обновляем статус
            if result.get('success'):
                await update_generation_status(generation_id, 'success')
                return True
            else:
                await update_generation_status(generation_id, 'failed')
                return False
                
        except Exception as e:
            self.logger.error(f"Ошибка повтора генерации {generation_id}: {e}", exc_info=True)
            return False