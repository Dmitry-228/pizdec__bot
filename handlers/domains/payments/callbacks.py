"""
Callback хендлеры домена платежей.
"""

import logging
from datetime import datetime, timedelta
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from config import TARIFFS
from database import check_database_user, get_user_registrations_by_date
from keyboards import create_subscription_keyboard, create_main_menu_keyboard
from states import BotStates
from ..common.base import BaseCallbackHandler
from ..common.decorators import log_handler_call, user_required
from ..common.types import CallbackResult
from .services import PaymentService, TariffService

logger = logging.getLogger(__name__)


class SubscriptionCallbackHandler(BaseCallbackHandler):
    """Хендлер для показа тарифов и подписок."""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.tariff_service = TariffService()
    
    @log_handler_call
    @user_required
    async def handle(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Показывает доступные тарифы."""
        user_id = query.from_user.id
        
        try:
            # Получаем данные пользователя
            user_data = await check_database_user(user_id)
            if not user_data:
                return CallbackResult.error_result("Пользователь не найден")
            
            # Определяем, является ли пользователь платящим
            is_paying_user = len(user_data) > 10 and user_data[10] > 0
            
            # Вычисляем время с регистрации
            registration_time = await self._get_registration_time(user_id)
            time_since_registration = (datetime.now() - registration_time).total_seconds() if registration_time else float('inf')
            
            # Получаем доступные тарифы
            available_tariffs = self.tariff_service.get_available_tariffs(
                is_paying_user, time_since_registration
            )
            
            # Формируем текст с тарифами
            tariff_text = self._format_tariff_text(user_data, available_tariffs)
            
            # Создаем клавиатуру с тарифами
            keyboard = await create_subscription_keyboard(
                hide_mini_tariff=time_since_registration <= 5400
            )
            
            await self.edit_safe_message(query.message, tariff_text, keyboard)
            
            return CallbackResult.success_result(
                message="Тарифы показаны",
                answer_text="💳 Выберите подходящий тариф"
            )
            
        except Exception as e:
            logger.error(f"Ошибка показа тарифов для user_id={user_id}: {e}", exc_info=True)
            return CallbackResult.error_result("Ошибка загрузки тарифов")
    
    async def _get_registration_time(self, user_id: int) -> datetime:
        """Получает время регистрации пользователя."""
        try:
            registrations = await get_user_registrations_by_date(user_id)
            if registrations:
                return registrations[0].get('created_at', datetime.now())
        except Exception as e:
            logger.warning(f"Не удалось получить время регистрации для user_id={user_id}: {e}")
        return datetime.now()
    
    def _format_tariff_text(self, user_data: tuple, available_tariffs: dict) -> str:
        """Форматирует текст с описанием тарифов."""
        first_purchase = user_data[5] if len(user_data) > 5 else True
        
        text_parts = [
            "🔥 Горячий выбор для идеальных фото и видео!",
            "",
            "Хочешь крутые кадры без лишних хлопот? Выбирай выгодный пакет и получай фото или видео в один клик!",
            ""
        ]
        
        # Добавляем описания тарифов
        for tariff_id, tariff in available_tariffs.items():
            text_parts.append(tariff.get('display', f"Тариф {tariff_id}"))
            text_parts.append("")
        
        # Бонус за первую покупку
        if first_purchase:
            text_parts.extend([
                "🎁 При первой покупке ЛЮБОГО пакета (кроме 'Только аватар') - 1 аватар в подарок!",
                ""
            ])
        
        text_parts.extend([
            "Выберите свой тариф ниже, нажав на соответствующую кнопку ⤵️",
            "",
            "📄 Приобретая пакет, вы соглашаетесь с [пользовательским соглашением](https://telegra.ph/Polzovatelskoe-soglashenie-07-26-12)"
        ])
        
        return "\n".join(text_parts)


class TariffCallbackHandler(BaseCallbackHandler):
    """Хендлер для обработки выбора конкретного тарифа."""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.tariff_service = TariffService()
        self.payment_service = PaymentService()
    
    @log_handler_call
    @user_required
    async def handle(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Обрабатывает выбор тарифа."""
        user_id = query.from_user.id
        callback_data = query.data
        
        # Извлекаем ID тарифа из callback_data
        tariff_id = callback_data.replace("tariff_", "").replace("buy_", "")
        
        # Проверяем существование тарифа
        tariff = self.tariff_service.get_tariff(tariff_id)
        if not tariff:
            return CallbackResult.error_result(f"Тариф '{tariff_id}' не найден")
        
        try:
            # Сохраняем выбранный тариф в состоянии
            await state.update_data(
                selected_tariff_id=tariff_id,
                tariff_amount=tariff['price'],
                tariff_description=self.payment_service.format_tariff_description(tariff_id)
            )
            
            # Запрашиваем email для оплаты
            await self._request_email(query, tariff)
            await state.set_state(BotStates.AWAITING_EMAIL)
            
            return CallbackResult.success_result(
                message=f"Выбран тариф {tariff_id}",
                answer_text=f"💳 Выбран тариф: {tariff['name']}"
            )
            
        except Exception as e:
            logger.error(f"Ошибка выбора тарифа {tariff_id} для user_id={user_id}: {e}", exc_info=True)
            return CallbackResult.error_result("Ошибка обработки тарифа")
    
    async def _request_email(self, query: CallbackQuery, tariff: dict):
        """Запрашивает email для создания платежа."""
        text = f"""
💳 **Выбран тариф: {tariff['name']}**

💰 Стоимость: {tariff['price']} RUB

📧 Для создания ссылки на оплату введите ваш email:

⚠️ Email нужен для отправки чека об оплате (требование закона)
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад к тарифам", callback_data="subscribe")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await self.edit_safe_message(query.message, text.strip(), keyboard)


class PaymentCallbackHandler(BaseCallbackHandler):
    """Хендлер для обработки платежных операций."""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.payment_service = PaymentService()
    
    @log_handler_call
    @user_required
    async def handle(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Обрабатывает платежные callback'и."""
        callback_data = query.data
        user_id = query.from_user.id
        
        if callback_data == "payment_success":
            return await self._handle_payment_success(query, state)
        elif callback_data == "payment_cancel":
            return await self._handle_payment_cancel(query, state)
        elif callback_data.startswith("payment_check_"):
            payment_id = callback_data.replace("payment_check_", "")
            return await self._handle_payment_check(query, state, payment_id)
        else:
            return CallbackResult.error_result("Неизвестная платежная операция")
    
    async def _handle_payment_success(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Обрабатывает успешный платеж."""
        user_id = query.from_user.id
        
        success_text = """
✅ **Платеж успешно обработан!**

🎉 Ваши ресурсы пополнены!
💰 Баланс обновлен

Спасибо за покупку! Теперь вы можете создавать еще больше потрясающих фото и видео.
        """
        
        keyboard = await create_main_menu_keyboard(user_id)
        await self.edit_safe_message(query.message, success_text.strip(), keyboard)
        await state.clear()
        
        return CallbackResult.success_result(
            message="Платеж успешно обработан",
            answer_text="✅ Платеж прошел успешно!"
        )
    
    async def _handle_payment_cancel(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Обрабатывает отмену платежа."""
        user_id = query.from_user.id
        
        cancel_text = """
❌ **Платеж отменен**

Ничего страшного! Вы можете вернуться к выбору тарифов в любое время.

Если у вас возникли вопросы, обратитесь в поддержку.
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Выбрать тариф", callback_data="subscribe")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await self.edit_safe_message(query.message, cancel_text.strip(), keyboard)
        await state.clear()
        
        return CallbackResult.success_result(
            message="Платеж отменен",
            answer_text="❌ Платеж отменен"
        )
    
    async def _handle_payment_check(self, query: CallbackQuery, state: FSMContext, payment_id: str) -> CallbackResult:
        """Проверяет статус платежа."""
        try:
            # Здесь можно реализовать проверку статуса через API YooKassa
            status = await self.payment_service.get_payment_status(payment_id)
            
            if status == "succeeded":
                return await self._handle_payment_success(query, state)
            elif status == "canceled":
                return await self._handle_payment_cancel(query, state)
            else:
                return CallbackResult.success_result(
                    message="Платеж в обработке",
                    answer_text="⏳ Платеж обрабатывается..."
                )
                
        except Exception as e:
            logger.error(f"Ошибка проверки платежа {payment_id}: {e}", exc_info=True)
            return CallbackResult.error_result("Ошибка проверки платежа")