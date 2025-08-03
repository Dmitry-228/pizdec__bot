"""
Message хендлеры домена платежей.
"""

import logging
import re
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from states import BotStates
from keyboards import create_main_menu_keyboard
from ..common.base import BaseMessageHandler
from ..common.decorators import log_handler_call, user_required
from ..common.types import HandlerResult, PaymentRequest
from .services import PaymentService

logger = logging.getLogger(__name__)


class EmailMessageHandler(BaseMessageHandler):
    """Хендлер для обработки ввода email при оплате."""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.payment_service = PaymentService()
    
    @log_handler_call
    @user_required
    async def handle(self, message: Message, state: FSMContext) -> HandlerResult:
        """Обрабатывает ввод email и создает ссылку на оплату."""
        user_id = message.from_user.id
        email = message.text.strip()
        
        # Валидация email
        if not self._is_valid_email(email):
            await self._send_email_error(message)
            return HandlerResult.error_result("Некорректный email")
        
        try:
            # Получаем данные о выбранном тарифе
            user_data = await state.get_data()
            tariff_id = user_data.get('selected_tariff_id')
            amount = user_data.get('tariff_amount')
            description = user_data.get('tariff_description')
            
            if not all([tariff_id, amount, description]):
                await self._send_tariff_error(message)
                return HandlerResult.error_result("Данные тарифа не найдены")
            
            # Создаем запрос на платеж
            payment_request = PaymentRequest(
                user_id=user_id,
                tariff_id=tariff_id,
                amount=float(amount),
                description=description,
                email=email
            )
            
            # Получаем username бота для return_url
            bot_info = await message.bot.get_me()
            bot_username = bot_info.username
            
            # Создаем ссылку на оплату
            payment_url = await self.payment_service.create_payment(payment_request, bot_username)
            
            # Отправляем ссылку пользователю
            await self._send_payment_link(message, payment_url, tariff_id, amount)
            
            # Очищаем состояние
            await state.clear()
            
            logger.info(f"Создана ссылка на оплату для user_id={user_id}, tariff={tariff_id}, email={email}")
            
            return HandlerResult.success_result(
                message="Ссылка на оплату создана",
                data={
                    "user_id": user_id,
                    "tariff_id": tariff_id,
                    "amount": amount,
                    "email": email,
                    "payment_url": payment_url
                }
            )
            
        except Exception as e:
            logger.error(f"Ошибка создания платежа для user_id={user_id}: {e}", exc_info=True)
            await self._send_payment_error(message)
            return HandlerResult.error_result(f"Ошибка создания платежа: {e}")
    
    def _is_valid_email(self, email: str) -> bool:
        """Проверяет корректность email адреса."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_pattern, email) is not None
    
    async def _send_email_error(self, message: Message):
        """Отправляет сообщение об ошибке email."""
        error_text = """
❌ **Некорректный email адрес**

Пожалуйста, введите корректный email адрес в формате: example@domain.com

Email нужен для отправки чека об оплате (требование закона).
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад к тарифам", callback_data="subscribe")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await self.send_safe_message(message.from_user.id, error_text.strip(), keyboard)
    
    async def _send_tariff_error(self, message: Message):
        """Отправляет сообщение об ошибке тарифа."""
        error_text = """
❌ **Ошибка: данные тарифа не найдены**

Пожалуйста, выберите тариф заново.
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Выбрать тариф", callback_data="subscribe")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await self.send_safe_message(message.from_user.id, error_text.strip(), keyboard)
    
    async def _send_payment_link(self, message: Message, payment_url: str, tariff_id: str, amount: float):
        """Отправляет ссылку на оплату."""
        success_text = f"""
💳 **Ссылка на оплату создана!**

📦 Тариф: {tariff_id}
💰 Сумма: {amount} RUB

👆 Нажмите на кнопку ниже для перехода к оплате

⚠️ Ссылка действительна в течение 15 минут
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Перейти к оплате", url=payment_url)],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await self.send_safe_message(message.from_user.id, success_text.strip(), keyboard)
    
    async def _send_payment_error(self, message: Message):
        """Отправляет сообщение об ошибке создания платежа."""
        error_text = """
❌ **Ошибка создания платежа**

Произошла техническая ошибка. Пожалуйста, попробуйте позже или обратитесь в поддержку.
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="subscribe")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await self.send_safe_message(message.from_user.id, error_text.strip(), keyboard)


class PaymentConfirmationHandler(BaseMessageHandler):
    """Хендлер для подтверждения платежей (если нужно)."""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.payment_service = PaymentService()
    
    @log_handler_call
    @user_required
    async def handle(self, message: Message, state: FSMContext) -> HandlerResult:
        """Обрабатывает подтверждение платежа."""
        user_id = message.from_user.id
        text = message.text.strip()
        
        # Проверяем, что это ID платежа или код подтверждения
        if not self._is_valid_payment_confirmation(text):
            await self._send_confirmation_error(message)
            return HandlerResult.error_result("Некорректный код подтверждения")
        
        try:
            # Проверяем статус платежа
            status = await self.payment_service.get_payment_status(text)
            
            if status == "succeeded":
                await self._send_success_confirmation(message)
                await state.clear()
                return HandlerResult.success_result("Платеж подтвержден")
            elif status == "pending":
                await self._send_pending_confirmation(message)
                return HandlerResult.success_result("Платеж в обработке")
            else:
                await self._send_failed_confirmation(message)
                return HandlerResult.error_result("Платеж не найден или отклонен")
                
        except Exception as e:
            logger.error(f"Ошибка подтверждения платежа для user_id={user_id}: {e}", exc_info=True)
            await self._send_confirmation_error(message)
            return HandlerResult.error_result(f"Ошибка подтверждения: {e}")
    
    def _is_valid_payment_confirmation(self, text: str) -> bool:
        """Проверяет корректность кода подтверждения."""
        # Простая проверка - код должен содержать буквы и цифры
        return len(text) >= 10 and any(c.isalnum() for c in text)
    
    async def _send_confirmation_error(self, message: Message):
        """Отправляет сообщение об ошибке подтверждения."""
        error_text = """
❌ **Некорректный код подтверждения**

Пожалуйста, введите корректный ID платежа или код подтверждения.
        """
        
        keyboard = await create_main_menu_keyboard(message.from_user.id)
        await self.send_safe_message(message.from_user.id, error_text.strip(), keyboard)
    
    async def _send_success_confirmation(self, message: Message):
        """Отправляет сообщение об успешном подтверждении."""
        success_text = """
✅ **Платеж успешно подтвержден!**

🎉 Ваши ресурсы пополнены!
💰 Баланс обновлен

Спасибо за покупку!
        """
        
        keyboard = await create_main_menu_keyboard(message.from_user.id)
        await self.send_safe_message(message.from_user.id, success_text.strip(), keyboard)
    
    async def _send_pending_confirmation(self, message: Message):
        """Отправляет сообщение о платеже в обработке."""
        pending_text = """
⏳ **Платеж в обработке**

Ваш платеж обрабатывается. Это может занять несколько минут.

Мы уведомим вас, когда платеж будет завершен.
        """
        
        keyboard = await create_main_menu_keyboard(message.from_user.id)
        await self.send_safe_message(message.from_user.id, pending_text.strip(), keyboard)
    
    async def _send_failed_confirmation(self, message: Message):
        """Отправляет сообщение о неудачном платеже."""
        failed_text = """
❌ **Платеж не найден или отклонен**

Возможные причины:
• Платеж еще не был совершен
• Платеж был отменен
• Неверный код подтверждения

Если вы считаете, что произошла ошибка, обратитесь в поддержку.
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Попробовать снова", callback_data="subscribe")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await self.send_safe_message(message.from_user.id, failed_text.strip(), keyboard)