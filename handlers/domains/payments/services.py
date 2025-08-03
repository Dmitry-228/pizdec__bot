"""
Сервисы для работы с платежами и тарифами.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from config import TARIFFS
from database import update_user_balance, save_payment, check_database_user
from handlers.utils import create_payment_link
from ..common.exceptions import PaymentError, ValidationError
from ..common.types import PaymentRequest

logger = logging.getLogger(__name__)


class TariffService:
    """Сервис для работы с тарифами."""
    
    @staticmethod
    def get_tariff(tariff_id: str) -> Optional[Dict[str, Any]]:
        """Получает информацию о тарифе."""
        return TARIFFS.get(tariff_id)
    
    @staticmethod
    def get_available_tariffs(is_paying_user: bool = False, time_since_registration: float = float('inf')) -> Dict[str, Any]:
        """Получает доступные тарифы для пользователя."""
        available_tariffs = {k: v for k, v in TARIFFS.items() if k != "admin_premium"}
        
        # Фильтрация тарифов для неоплативших пользователей
        if not is_paying_user:
            if time_since_registration <= 1800:  # 30 минут
                available_tariffs = {k: v for k, v in available_tariffs.items() if k in ["комфорт"]}
            elif time_since_registration <= 5400:  # 30–90 минут
                available_tariffs = {k: v for k, v in available_tariffs.items() if k in ["комфорт", "лайт"]}
            # После 90 минут "мини" доступен
        
        return available_tariffs
    
    @staticmethod
    def validate_tariff(tariff_id: str) -> bool:
        """Проверяет существование тарифа."""
        return tariff_id in TARIFFS
    
    @staticmethod
    def calculate_bonus_resources(tariff_id: str, is_first_purchase: bool = False) -> Dict[str, int]:
        """Рассчитывает бонусные ресурсы для тарифа."""
        tariff = TARIFFS.get(tariff_id)
        if not tariff:
            return {"photos": 0, "avatars": 0}
        
        bonus_resources = {
            "photos": tariff.get("photos", 0),
            "avatars": tariff.get("avatars", 0)
        }
        
        # Бонус за первую покупку (кроме тарифа "только аватар")
        if is_first_purchase and tariff_id != "только_аватар":
            bonus_resources["avatars"] += 1
        
        return bonus_resources


class PaymentService:
    """Сервис для работы с платежами."""
    
    def __init__(self):
        self.tariff_service = TariffService()
    
    async def create_payment(self, payment_request: PaymentRequest, bot_username: str) -> str:
        """Создает платеж и возвращает ссылку на оплату."""
        # Валидация тарифа
        if not self.tariff_service.validate_tariff(payment_request.tariff_id):
            raise ValidationError(f"Неизвестный тариф: {payment_request.tariff_id}")
        
        # Валидация email
        if not payment_request.email or "@" not in payment_request.email:
            raise ValidationError("Некорректный email адрес")
        
        try:
            # Создаем ссылку на оплату
            payment_url = await create_payment_link(
                user_id=payment_request.user_id,
                email=payment_request.email,
                amount_value=payment_request.amount,
                description=payment_request.description,
                bot_username=bot_username
            )
            
            logger.info(f"Создана ссылка на оплату для user_id={payment_request.user_id}, "
                       f"tariff={payment_request.tariff_id}, amount={payment_request.amount}")
            
            return payment_url
            
        except Exception as e:
            logger.error(f"Ошибка создания платежа: {e}", exc_info=True)
            raise PaymentError(f"Не удалось создать платеж: {e}")
    
    async def process_successful_payment(
        self, 
        user_id: int, 
        tariff_id: str, 
        amount: float,
        payment_id: str = None
    ) -> bool:
        """Обрабатывает успешный платеж."""
        try:
            # Получаем информацию о пользователе
            user_data = await check_database_user(user_id)
            if not user_data:
                raise ValidationError(f"Пользователь {user_id} не найден")
            
            # Определяем, первая ли это покупка
            is_first_purchase = user_data[5] if len(user_data) > 5 else True
            
            # Рассчитываем ресурсы для выдачи
            bonus_resources = self.tariff_service.calculate_bonus_resources(
                tariff_id, is_first_purchase
            )
            
            # Выдаем ресурсы пользователю
            if bonus_resources["photos"] > 0:
                await update_user_balance(user_id, "increment_photo", bonus_resources["photos"])
            
            if bonus_resources["avatars"] > 0:
                await update_user_balance(user_id, "increment_avatar", bonus_resources["avatars"])
            
            # Отмечаем, что пользователь совершил покупку
            if is_first_purchase:
                await update_user_balance(user_id, "mark_first_purchase")
            
            # Сохраняем информацию о платеже
            await save_payment(
                user_id=user_id,
                amount=amount,
                tariff_id=tariff_id,
                payment_id=payment_id or f"manual_{datetime.now().isoformat()}",
                status="succeeded"
            )
            
            logger.info(f"Успешно обработан платеж: user_id={user_id}, tariff={tariff_id}, "
                       f"amount={amount}, photos=+{bonus_resources['photos']}, "
                       f"avatars=+{bonus_resources['avatars']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обработки платежа: {e}", exc_info=True)
            raise PaymentError(f"Не удалось обработать платеж: {e}")
    
    async def get_payment_status(self, payment_id: str) -> Optional[str]:
        """Получает статус платежа."""
        # Здесь можно реализовать запрос к YooKassa API для получения статуса
        # Пока возвращаем None
        return None
    
    def format_tariff_description(self, tariff_id: str) -> str:
        """Форматирует описание тарифа для платежа."""
        tariff = self.tariff_service.get_tariff(tariff_id)
        if not tariff:
            return f"Тариф {tariff_id}"
        
        description_parts = []
        
        if tariff.get("photos", 0) > 0:
            description_parts.append(f"{tariff['photos']} печенек")
        
        if tariff.get("avatars", 0) > 0:
            description_parts.append(f"{tariff['avatars']} аватаров")
        
        if description_parts:
            return f"PixelPie: {' + '.join(description_parts)}"
        else:
            return f"PixelPie: {tariff.get('name', tariff_id)}"