"""
Базовые классы для всех хендлеров.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Any, Dict, Union
from aiogram import Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode

from handlers.utils import (
    safe_escape_markdown, send_message_with_fallback, 
    safe_edit_message, send_typing_action
)
from .types import HandlerResult, CallbackResult
from .exceptions import HandlerError, ValidationError

logger = logging.getLogger(__name__)


class BaseHandler(ABC):
    """Базовый класс для всех хендлеров."""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def send_typing(self, chat_id: int) -> None:
        """Отправляет индикатор печати."""
        await send_typing_action(self.bot, chat_id)
    
    async def send_safe_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        parse_mode: Optional[str] = ParseMode.MARKDOWN_V2
    ) -> Optional[Message]:
        """Безопасно отправляет сообщение с обработкой ошибок."""
        escaped_text = safe_escape_markdown(text, version=2)
        return await send_message_with_fallback(
            self.bot, chat_id, escaped_text, reply_markup, parse_mode
        )
    
    async def edit_safe_message(
        self,
        message: Message,
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        parse_mode: Optional[str] = ParseMode.MARKDOWN_V2
    ) -> Optional[Message]:
        """Безопасно редактирует сообщение."""
        escaped_text = safe_escape_markdown(text, version=2)
        return await safe_edit_message(message, escaped_text, reply_markup, parse_mode)
    
    def validate_user_data(self, data: Dict[str, Any], required_fields: list) -> None:
        """Валидирует данные пользователя."""
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise ValidationError(f"Отсутствуют обязательные поля: {missing_fields}")
    
    async def handle_error(self, error: Exception, user_id: int) -> None:
        """Обрабатывает ошибки и уведомляет пользователя."""
        self.logger.error(f"Ошибка в хендлере {self.__class__.__name__}: {error}", exc_info=True)
        
        if isinstance(error, ValidationError):
            error_text = f"❌ Ошибка валидации: {error}"
        elif isinstance(error, HandlerError):
            error_text = f"❌ {error}"
        else:
            error_text = "❌ Произошла внутренняя ошибка. Попробуйте позже."
        
        await self.send_safe_message(user_id, error_text)


class BaseCallbackHandler(BaseHandler):
    """Базовый класс для обработчиков callback запросов."""
    
    @abstractmethod
    async def handle(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Обрабатывает callback запрос."""
        pass
    
    async def answer_callback(self, query: CallbackQuery, text: str = None, show_alert: bool = False) -> None:
        """Отвечает на callback запрос."""
        try:
            await query.answer(text=text, show_alert=show_alert)
        except Exception as e:
            self.logger.warning(f"Не удалось ответить на callback: {e}")
    
    async def process_callback(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Основной метод обработки callback с обработкой ошибок."""
        try:
            await self.send_typing(query.from_user.id)
            result = await self.handle(query, state)
            await self.answer_callback(query)
            return result
        except Exception as e:
            await self.handle_error(e, query.from_user.id)
            await self.answer_callback(query, "❌ Произошла ошибка", show_alert=True)
            return CallbackResult(success=False, error=str(e))


class BaseMessageHandler(BaseHandler):
    """Базовый класс для обработчиков сообщений."""
    
    @abstractmethod
    async def handle(self, message: Message, state: FSMContext) -> HandlerResult:
        """Обрабатывает сообщение."""
        pass
    
    async def process_message(self, message: Message, state: FSMContext) -> HandlerResult:
        """Основной метод обработки сообщения с обработкой ошибок."""
        try:
            await self.send_typing(message.from_user.id)
            return await self.handle(message, state)
        except Exception as e:
            await self.handle_error(e, message.from_user.id)
            return HandlerResult(success=False, error=str(e))


class BaseDomainHandler(BaseHandler):
    """Базовый класс для доменных хендлеров."""
    
    def __init__(self, bot: Bot):
        super().__init__(bot)
        self.callbacks: Dict[str, BaseCallbackHandler] = {}
        self.messages: Dict[str, BaseMessageHandler] = {}
    
    def register_callback(self, pattern: str, handler: BaseCallbackHandler) -> None:
        """Регистрирует callback хендлер."""
        self.callbacks[pattern] = handler
    
    def register_message(self, pattern: str, handler: BaseMessageHandler) -> None:
        """Регистрирует message хендлер."""
        self.messages[pattern] = handler
    
    async def route_callback(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Маршрутизирует callback к соответствующему хендлеру."""
        callback_data = query.data
        
        for pattern, handler in self.callbacks.items():
            if callback_data.startswith(pattern):
                return await handler.process_callback(query, state)
        
        self.logger.warning(f"Не найден хендлер для callback: {callback_data}")
        return CallbackResult(success=False, error="Handler not found")
    
    async def route_message(self, message: Message, state: FSMContext) -> HandlerResult:
        """Маршрутизирует сообщение к соответствующему хендлеру."""
        # Логика маршрутизации сообщений может быть более сложной
        # В зависимости от состояния FSM или содержимого сообщения
        
        current_state = await state.get_state()
        
        if current_state in self.messages:
            handler = self.messages[current_state]
            return await handler.process_message(message, state)
        
        self.logger.warning(f"Не найден хендлер для состояния: {current_state}")
        return HandlerResult(success=False, error="Handler not found")