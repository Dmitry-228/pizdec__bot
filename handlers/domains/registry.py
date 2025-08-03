"""
Реестр доменов - центральная точка управления всеми доменными хендлерами.
"""

import logging
from typing import Dict, Optional
from aiogram import Bot, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from .auth.handlers import AuthDomainHandler
from .payments.handlers import PaymentsDomainHandler
from .generation.handlers import GenerationDomainHandler
from .user.handlers import UserDomainHandler
from .admin.handlers import AdminDomainHandler
from .broadcast.handlers import BroadcastDomainHandler
from .common.base import BaseDomainHandler
from .common.types import HandlerResult, CallbackResult

logger = logging.getLogger(__name__)


class DomainRegistry:
    """Реестр всех доменных хендлеров."""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.domains: Dict[str, BaseDomainHandler] = {}
        self._initialize_domains()
    
    def _initialize_domains(self):
        """Инициализирует все домены."""
        try:
            self.domains = {
                'auth': AuthDomainHandler(self.bot),
                'payments': PaymentsDomainHandler(self.bot),
                'generation': GenerationDomainHandler(self.bot),
                'user': UserDomainHandler(self.bot),
                'admin': AdminDomainHandler(self.bot),
                'broadcast': BroadcastDomainHandler(self.bot),
            }
            logger.info(f"Инициализированы домены: {list(self.domains.keys())}")
        except Exception as e:
            logger.error(f"Ошибка инициализации доменов: {e}", exc_info=True)
            # Инициализируем только базовые домены в случае ошибки
            self.domains = {
                'auth': AuthDomainHandler(self.bot),
            }
    
    def get_domain(self, domain_name: str) -> Optional[BaseDomainHandler]:
        """Получает домен по имени."""
        return self.domains.get(domain_name)
    
    async def route_callback(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Маршрутизирует callback к соответствующему домену."""
        callback_data = query.data
        user_id = query.from_user.id
        
        logger.debug(f"Маршрутизация callback: {callback_data} от user_id={user_id}")
        
        # Определяем домен по префиксу callback_data
        domain_name = self._determine_callback_domain(callback_data)
        
        if domain_name and domain_name in self.domains:
            domain = self.domains[domain_name]
            try:
                return await domain.route_callback(query, state)
            except Exception as e:
                logger.error(f"Ошибка в домене {domain_name}: {e}", exc_info=True)
                return CallbackResult.error_result(f"Ошибка обработки: {e}")
        
        # Fallback для неизвестных callback'ов
        logger.warning(f"Не найден домен для callback: {callback_data}")
        return CallbackResult.error_result("Неизвестная команда")
    
    async def route_message(self, message: Message, state: FSMContext) -> HandlerResult:
        """Маршрутизирует сообщение к соответствующему домену."""
        user_id = message.from_user.id
        current_state = await state.get_state()
        
        logger.debug(f"Маршрутизация сообщения от user_id={user_id}, state={current_state}")
        
        # Определяем домен по состоянию FSM или содержимому сообщения
        domain_name = self._determine_message_domain(message, current_state)
        
        if domain_name and domain_name in self.domains:
            domain = self.domains[domain_name]
            try:
                return await domain.route_message(message, state)
            except Exception as e:
                logger.error(f"Ошибка в домене {domain_name}: {e}", exc_info=True)
                return HandlerResult.error_result(f"Ошибка обработки: {e}")
        
        # Fallback для неизвестных сообщений
        logger.warning(f"Не найден домен для сообщения от user_id={user_id}")
        return HandlerResult.error_result("Неизвестная команда")
    
    def _determine_callback_domain(self, callback_data: str) -> Optional[str]:
        """Определяет домен по callback_data."""
        # Маппинг префиксов callback'ов к доменам
        callback_domain_map = {
            # Auth domain
            'main_menu': 'auth',
            'back_to_menu': 'auth',
            'referral_': 'auth',
            
            # Payments domain
            'subscribe': 'payments',
            'tariff_': 'payments',
            'payment_': 'payments',
            'buy_': 'payments',
            
            # Generation domain
            'generate_': 'generation',
            'style_': 'generation',
            'photo_': 'generation',
            'video_': 'generation',
            'avatar_': 'generation',
            
            # User domain
            'profile': 'user',
            'my_avatars': 'user',
            'user_settings': 'user',
            'change_avatar_': 'user',
            'select_avatar_': 'user',
            
            # Admin domain
            'admin_': 'admin',
            'user_actions_': 'admin',
            'view_user_': 'admin',
            
            # Broadcast domain
            'broadcast_': 'broadcast',
        }
        
        for prefix, domain in callback_domain_map.items():
            if callback_data.startswith(prefix):
                return domain
        
        return None
    
    def _determine_message_domain(self, message: Message, current_state: str) -> Optional[str]:
        """Определяет домен по сообщению и состоянию."""
        # Команды
        if message.text and message.text.startswith('/'):
            command = message.text.split()[0].lower()
            command_domain_map = {
                '/start': 'auth',
                '/menu': 'auth',
                '/help': 'auth',
                '/admin': 'admin',
                '/broadcast': 'broadcast',
            }
            return command_domain_map.get(command)
        
        # Состояния FSM
        if current_state:
            state_domain_map = {
                # Generation states
                'awaiting_prompt': 'generation',
                'awaiting_face_image': 'generation',
                'awaiting_style_selection': 'generation',
                
                # Broadcast states
                'awaiting_broadcast_message': 'broadcast',
                'awaiting_broadcast_media': 'broadcast',
                
                # Admin states
                'awaiting_admin_prompt': 'admin',
                'awaiting_chat_message': 'admin',
                
                # User states
                'awaiting_email': 'user',
                'awaiting_avatar_name': 'user',
            }
            
            for state_prefix, domain in state_domain_map.items():
                if current_state.startswith(state_prefix):
                    return domain
        
        # По типу контента
        if message.photo:
            return 'generation'
        elif message.video:
            return 'generation'
        elif message.text:
            # Простая эвристика для определения домена по тексту
            text_lower = message.text.lower()
            if any(word in text_lower for word in ['генерация', 'фото', 'картинка', 'изображение']):
                return 'generation'
            elif any(word in text_lower for word in ['профиль', 'аватар', 'настройки']):
                return 'user'
        
        # По умолчанию - auth домен (для обработки неизвестных команд)
        return 'auth'
    
    def create_router(self) -> Router:
        """Создает роутер с обработчиками всех доменов."""
        router = Router()
        
        # Регистрируем обработчики callback'ов
        @router.callback_query()
        async def handle_callback(query: CallbackQuery, state: FSMContext):
            result = await self.route_callback(query, state)
            if not result.success:
                logger.error(f"Ошибка обработки callback: {result.error}")
        
        # Регистрируем обработчики сообщений
        @router.message()
        async def handle_message(message: Message, state: FSMContext):
            result = await self.route_message(message, state)
            if not result.success:
                logger.error(f"Ошибка обработки сообщения: {result.error}")
        
        return router