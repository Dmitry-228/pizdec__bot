"""
Webhook хендлеры для обработки уведомлений от платежных систем.
"""

import json
import logging
from typing import Dict, Any, Optional
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import YOOKASSA_SECRET_KEY
from keyboards import create_main_menu_keyboard
from ..common.exceptions import PaymentError
from .services import PaymentService

logger = logging.getLogger(__name__)


class PaymentWebhookHandler:
    """Обработчик webhook'ов от платежных систем."""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.payment_service = PaymentService()
    
    async def handle_yookassa_webhook(self, webhook_data: Dict[str, Any]) -> bool:
        """Обрабатывает webhook от YooKassa."""
        try:
            # Валидация webhook'а
            if not self._validate_yookassa_webhook(webhook_data):
                logger.warning("Невалидный YooKassa webhook")
                return False
            
            # Извлекаем данные о платеже
            event_type = webhook_data.get('event')
            payment_object = webhook_data.get('object', {})
            
            if event_type == 'payment.succeeded':
                return await self._handle_payment_succeeded(payment_object)
            elif event_type == 'payment.canceled':
                return await self._handle_payment_canceled(payment_object)
            elif event_type == 'payment.waiting_for_capture':
                return await self._handle_payment_waiting(payment_object)
            else:
                logger.info(f"Неизвестный тип события YooKassa: {event_type}")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка обработки YooKassa webhook: {e}", exc_info=True)
            return False
    
    def _validate_yookassa_webhook(self, webhook_data: Dict[str, Any]) -> bool:
        """Валидирует webhook от YooKassa."""
        # Проверяем наличие обязательных полей
        required_fields = ['event', 'object']
        if not all(field in webhook_data for field in required_fields):
            return False
        
        # Проверяем структуру объекта платежа
        payment_object = webhook_data.get('object', {})
        if not isinstance(payment_object, dict):
            return False
        
        # Проверяем наличие ID платежа
        if 'id' not in payment_object:
            return False
        
        # Здесь можно добавить проверку подписи webhook'а
        # if YOOKASSA_SECRET_KEY:
        #     return self._verify_webhook_signature(webhook_data)
        
        return True
    
    async def _handle_payment_succeeded(self, payment_object: Dict[str, Any]) -> bool:
        """Обрабатывает успешный платеж."""
        try:
            payment_id = payment_object.get('id')
            amount_value = float(payment_object.get('amount', {}).get('value', 0))
            metadata = payment_object.get('metadata', {})
            
            user_id = int(metadata.get('user_id', 0))
            if not user_id:
                logger.error(f"Не найден user_id в metadata платежа {payment_id}")
                return False
            
            # Определяем тариф по сумме платежа
            tariff_id = self._determine_tariff_by_amount(amount_value)
            if not tariff_id:
                logger.error(f"Не удалось определить тариф для суммы {amount_value}")
                return False
            
            # Обрабатываем успешный платеж
            success = await self.payment_service.process_successful_payment(
                user_id=user_id,
                tariff_id=tariff_id,
                amount=amount_value,
                payment_id=payment_id
            )
            
            if success:
                # Уведомляем пользователя об успешном платеже
                await self._notify_user_payment_success(user_id, tariff_id, amount_value)
                logger.info(f"Успешно обработан платеж {payment_id} для user_id={user_id}")
                return True
            else:
                logger.error(f"Не удалось обработать платеж {payment_id}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка обработки успешного платежа: {e}", exc_info=True)
            return False
    
    async def _handle_payment_canceled(self, payment_object: Dict[str, Any]) -> bool:
        """Обрабатывает отмененный платеж."""
        try:
            payment_id = payment_object.get('id')
            metadata = payment_object.get('metadata', {})
            user_id = int(metadata.get('user_id', 0))
            
            if user_id:
                await self._notify_user_payment_canceled(user_id, payment_id)
                logger.info(f"Платеж {payment_id} отменен для user_id={user_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обработки отмененного платежа: {e}", exc_info=True)
            return False
    
    async def _handle_payment_waiting(self, payment_object: Dict[str, Any]) -> bool:
        """Обрабатывает платеж, ожидающий подтверждения."""
        try:
            payment_id = payment_object.get('id')
            metadata = payment_object.get('metadata', {})
            user_id = int(metadata.get('user_id', 0))
            
            if user_id:
                await self._notify_user_payment_waiting(user_id, payment_id)
                logger.info(f"Платеж {payment_id} ожидает подтверждения для user_id={user_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обработки ожидающего платежа: {e}", exc_info=True)
            return False
    
    def _determine_tariff_by_amount(self, amount: float) -> Optional[str]:
        """Определяет тариф по сумме платежа."""
        from config import TARIFFS
        
        # Ищем тариф с соответствующей ценой
        for tariff_id, tariff_data in TARIFFS.items():
            if abs(tariff_data.get('price', 0) - amount) < 0.01:  # Учитываем погрешность
                return tariff_id
        
        return None
    
    async def _notify_user_payment_success(self, user_id: int, tariff_id: str, amount: float):
        """Уведомляет пользователя об успешном платеже."""
        try:
            success_text = f"""
✅ **Платеж успешно обработан!**

💳 Тариф: {tariff_id}
💰 Сумма: {amount} RUB

🎉 Ваши ресурсы пополнены!
💰 Баланс обновлен

Спасибо за покупку! Теперь вы можете создавать еще больше потрясающих фото и видео.
            """
            
            keyboard = await create_main_menu_keyboard(user_id)
            
            await self.bot.send_message(
                chat_id=user_id,
                text=success_text.strip(),
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Не удалось уведомить пользователя {user_id} об успешном платеже: {e}")
    
    async def _notify_user_payment_canceled(self, user_id: int, payment_id: str):
        """Уведомляет пользователя об отмененном платеже."""
        try:
            cancel_text = f"""
❌ **Платеж отменен**

ID платежа: {payment_id}

Ничего страшного! Вы можете попробовать оплатить снова или выбрать другой тариф.

Если у вас возникли вопросы, обратитесь в поддержку.
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 Выбрать тариф", callback_data="subscribe")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ])
            
            await self.bot.send_message(
                chat_id=user_id,
                text=cancel_text.strip(),
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Не удалось уведомить пользователя {user_id} об отмененном платеже: {e}")
    
    async def _notify_user_payment_waiting(self, user_id: int, payment_id: str):
        """Уведомляет пользователя о платеже в ожидании."""
        try:
            waiting_text = f"""
⏳ **Платеж обрабатывается**

ID платежа: {payment_id}

Ваш платеж принят и обрабатывается. Это может занять несколько минут.

Мы уведомим вас, когда обработка будет завершена.
            """
            
            keyboard = await create_main_menu_keyboard(user_id)
            
            await self.bot.send_message(
                chat_id=user_id,
                text=waiting_text.strip(),
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Не удалось уведомить пользователя {user_id} о платеже в ожидании: {e}")


class ManualPaymentHandler:
    """Обработчик для ручной обработки платежей администратором."""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.payment_service = PaymentService()
    
    async def process_manual_payment(
        self, 
        user_id: int, 
        tariff_id: str, 
        amount: float,
        admin_id: int,
        note: str = None
    ) -> bool:
        """Обрабатывает ручной платеж от администратора."""
        try:
            # Обрабатываем платеж
            success = await self.payment_service.process_successful_payment(
                user_id=user_id,
                tariff_id=tariff_id,
                amount=amount,
                payment_id=f"manual_{admin_id}_{user_id}"
            )
            
            if success:
                # Уведомляем пользователя
                await self._notify_user_manual_payment(user_id, tariff_id, amount, note)
                
                # Уведомляем администратора
                await self._notify_admin_manual_payment(admin_id, user_id, tariff_id, amount)
                
                logger.info(f"Ручной платеж обработан: user_id={user_id}, tariff={tariff_id}, admin={admin_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка обработки ручного платежа: {e}", exc_info=True)
            return False
    
    async def _notify_user_manual_payment(self, user_id: int, tariff_id: str, amount: float, note: str):
        """Уведомляет пользователя о ручном пополнении."""
        try:
            text = f"""
🎁 **Ваш баланс пополнен администратором!**

💳 Тариф: {tariff_id}
💰 Сумма: {amount} RUB

🎉 Ваши ресурсы пополнены!
            """
            
            if note:
                text += f"\n📝 Примечание: {note}"
            
            keyboard = await create_main_menu_keyboard(user_id)
            
            await self.bot.send_message(
                chat_id=user_id,
                text=text.strip(),
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Не удалось уведомить пользователя {user_id} о ручном пополнении: {e}")
    
    async def _notify_admin_manual_payment(self, admin_id: int, user_id: int, tariff_id: str, amount: float):
        """Уведомляет администратора об успешном ручном пополнении."""
        try:
            text = f"""
✅ **Ручное пополнение выполнено**

👤 Пользователь: {user_id}
💳 Тариф: {tariff_id}
💰 Сумма: {amount} RUB

Ресурсы успешно добавлены пользователю.
            """
            
            await self.bot.send_message(
                chat_id=admin_id,
                text=text.strip(),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Не удалось уведомить администратора {admin_id} о ручном пополнении: {e}")