"""
Callback хендлеры домена аутентификации.
"""

import logging
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from database import get_user_referrals, check_database_user
from keyboards import create_main_menu_keyboard
from ..common.base import BaseCallbackHandler
from ..common.decorators import log_handler_call
from ..common.types import CallbackResult

logger = logging.getLogger(__name__)


class ReferralCallbackHandler(BaseCallbackHandler):
    """Хендлер реферальных callback'ов."""
    
    @log_handler_call
    async def handle(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Обрабатывает реферальные callback'и."""
        user_id = query.from_user.id
        callback_data = query.data
        
        if callback_data == "referral_info":
            return await self._show_referral_info(query, user_id)
        elif callback_data == "referral_stats":
            return await self._show_referral_stats(query, user_id)
        else:
            return CallbackResult.error_result("Неизвестная реферальная команда")
    
    async def _show_referral_info(self, query: CallbackQuery, user_id: int) -> CallbackResult:
        """Показывает информацию о реферальной программе."""
        referral_link = f"https://t.me/{query.bot.username}?start={user_id}"
        
        info_text = f"""
🎯 **Реферальная программа**

Приглашайте друзей и получайте бонусы!

**Ваша реферальная ссылка:**
`{referral_link}`

**Как это работает:**
• Поделитесь ссылкой с друзьями
• Когда друг регистрируется по вашей ссылке, вы оба получаете бонусы
• Чем больше друзей - тем больше бонусов!

**Бонусы:**
• 🍪 +5 печенек за каждого приглашенного друга
• 🎭 +1 аватар за каждые 5 приглашенных друзей

Начните приглашать прямо сейчас! 🚀
        """
        
        await self.edit_safe_message(query.message, info_text.strip())
        
        return CallbackResult.success_result(
            message="Информация о реферальной программе показана",
            answer_text="📋 Информация о реферальной программе"
        )
    
    async def _show_referral_stats(self, query: CallbackQuery, user_id: int) -> CallbackResult:
        """Показывает статистику рефералов пользователя."""
        try:
            # Получаем статистику рефералов
            referrals = await get_user_referrals(user_id)
            referral_count = len(referrals) if referrals else 0
            
            # Получаем данные пользователя для подсчета бонусов
            user_data = await check_database_user(user_id)
            if not user_data:
                return CallbackResult.error_result("Пользователь не найден")
            
            # Подсчитываем полученные бонусы
            bonus_photos = referral_count * 5
            bonus_avatars = referral_count // 5
            
            stats_text = f"""
📊 **Ваша реферальная статистика**

👥 **Приглашено друзей:** {referral_count}

🎁 **Получено бонусов:**
• 🍪 Печеньки: +{bonus_photos}
• 🎭 Аватары: +{bonus_avatars}

📈 **Прогресс до следующего аватара:**
{referral_count % 5}/5 рефералов
            """
            
            if referrals:
                stats_text += "\n\n👥 **Ваши рефералы:**\n"
                for i, referral in enumerate(referrals[:10], 1):  # Показываем только первые 10
                    ref_name = referral.get('first_name', 'Пользователь')
                    ref_username = referral.get('username', '')
                    if ref_username:
                        stats_text += f"{i}. {ref_name} (@{ref_username})\n"
                    else:
                        stats_text += f"{i}. {ref_name}\n"
                
                if len(referrals) > 10:
                    stats_text += f"... и еще {len(referrals) - 10} рефералов\n"
            
            await self.edit_safe_message(query.message, stats_text.strip())
            
            return CallbackResult.success_result(
                message="Статистика рефералов показана",
                answer_text="📊 Статистика обновлена"
            )
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики рефералов для {user_id}: {e}", exc_info=True)
            return CallbackResult.error_result("Ошибка получения статистики")


class MenuCallbackHandler(BaseCallbackHandler):
    """Хендлер callback'ов главного меню."""
    
    @log_handler_call
    async def handle(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Обрабатывает callback'и главного меню."""
        user_id = query.from_user.id
        callback_data = query.data
        
        if callback_data == "main_menu":
            return await self._show_main_menu(query, user_id)
        elif callback_data == "back_to_menu":
            return await self._show_main_menu(query, user_id)
        else:
            return CallbackResult.error_result("Неизвестная команда меню")
    
    async def _show_main_menu(self, query: CallbackQuery, user_id: int) -> CallbackResult:
        """Показывает главное меню."""
        await state.clear()  # Очищаем состояние при возврате в меню
        
        welcome_text = "🏠 Главное меню\n\nВыберите действие:"
        reply_markup = await create_main_menu_keyboard(user_id)
        
        await self.edit_safe_message(query.message, welcome_text, reply_markup)
        
        return CallbackResult.success_result(
            message="Главное меню показано",
            answer_text="🏠 Главное меню"
        )