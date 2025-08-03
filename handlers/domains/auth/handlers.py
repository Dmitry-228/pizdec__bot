"""
Основные хендлеры домена аутентификации.
"""

from aiogram import Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from ..common.base import BaseDomainHandler
from ..common.decorators import log_handler_call
from ..common.types import HandlerResult, CallbackResult
from .commands import StartCommandHandler
from .callbacks import ReferralCallbackHandler


class AuthDomainHandler(BaseDomainHandler):
    """Основной хендлер домена аутентификации."""
    
    def __init__(self, bot: Bot):
        super().__init__(bot)
        self._register_handlers()
    
    def _register_handlers(self):
        """Регистрирует хендлеры домена."""
        # Команды
        self.register_message("start", StartCommandHandler(self.bot))
        
        # Callback'и
        self.register_callback("referral_", ReferralCallbackHandler(self.bot))
    
    @log_handler_call
    async def handle_start_command(self, message: Message, state: FSMContext) -> HandlerResult:
        """Обрабатывает команду /start."""
        handler = self.messages.get("start")
        if handler:
            return await handler.process_message(message, state)
        return HandlerResult.error_result("Handler not found")
    
    @log_handler_call
    async def handle_referral_callback(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Обрабатывает реферальные callback'и."""
        return await self.route_callback(query, state)