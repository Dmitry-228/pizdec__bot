"""
Основные хендлеры домена платежей.
"""

from aiogram import Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from states import BotStates
from ..common.base import BaseDomainHandler
from ..common.decorators import log_handler_call
from ..common.types import HandlerResult, CallbackResult
from .callbacks import SubscriptionCallbackHandler, TariffCallbackHandler, PaymentCallbackHandler
from .messages import EmailMessageHandler, PaymentConfirmationHandler
from .webhooks import PaymentWebhookHandler, ManualPaymentHandler


class PaymentsDomainHandler(BaseDomainHandler):
    """Основной хендлер домена платежей."""
    
    def __init__(self, bot: Bot):
        super().__init__(bot)
        self.webhook_handler = PaymentWebhookHandler(bot)
        self.manual_payment_handler = ManualPaymentHandler(bot)
        self._register_handlers()
    
    def _register_handlers(self):
        """Регистрирует хендлеры домена."""
        # Callback хендлеры
        self.register_callback("subscribe", SubscriptionCallbackHandler(self.bot))
        self.register_callback("tariff_", TariffCallbackHandler(self.bot))
        self.register_callback("buy_", TariffCallbackHandler(self.bot))  # Альтернативный префикс
        self.register_callback("payment_", PaymentCallbackHandler(self.bot))
        
        # Message хендлеры по состояниям FSM
        self.register_message(BotStates.AWAITING_EMAIL, EmailMessageHandler(self.bot))
        self.register_message(BotStates.AWAITING_PAYMENT_CONFIRMATION, PaymentConfirmationHandler(self.bot))
    
    @log_handler_call
    async def handle_subscription_callback(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Обрабатывает callback для показа тарифов."""
        handler = self.callbacks.get("subscribe")
        if handler:
            return await handler.process_callback(query, state)
        return CallbackResult.error_result("Handler not found")
    
    @log_handler_call
    async def handle_tariff_callback(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Обрабатывает callback выбора тарифа."""
        callback_data = query.data
        
        # Определяем подходящий хендлер
        if callback_data.startswith("tariff_") or callback_data.startswith("buy_"):
            handler = self.callbacks.get("tariff_")
        elif callback_data.startswith("payment_"):
            handler = self.callbacks.get("payment_")
        else:
            return CallbackResult.error_result("Unknown payment callback")
        
        if handler:
            return await handler.process_callback(query, state)
        return CallbackResult.error_result("Handler not found")
    
    @log_handler_call
    async def handle_email_message(self, message: Message, state: FSMContext) -> HandlerResult:
        """Обрабатывает ввод email для оплаты."""
        current_state = await state.get_state()
        
        if current_state == BotStates.AWAITING_EMAIL:
            handler = self.messages.get(BotStates.AWAITING_EMAIL)
            if handler:
                return await handler.process_message(message, state)
        
        return HandlerResult.error_result("Invalid state for email input")
    
    # Webhook методы
    async def handle_yookassa_webhook(self, webhook_data: dict) -> bool:
        """Обрабатывает webhook от YooKassa."""
        return await self.webhook_handler.handle_yookassa_webhook(webhook_data)
    
    # Административные методы
    async def process_manual_payment(
        self, 
        user_id: int, 
        tariff_id: str, 
        amount: float,
        admin_id: int,
        note: str = None
    ) -> bool:
        """Обрабатывает ручное пополнение от администратора."""
        return await self.manual_payment_handler.process_manual_payment(
            user_id, tariff_id, amount, admin_id, note
        )