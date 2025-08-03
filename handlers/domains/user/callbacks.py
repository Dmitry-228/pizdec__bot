"""
Callback хендлеры пользовательского домена.
"""

import logging
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from keyboards import create_user_profile_keyboard, create_main_menu_keyboard
from states import BotStates
from ..common.base import BaseCallbackHandler
from ..common.decorators import log_handler_call, user_required
from ..common.types import CallbackResult
from .services import UserService, AvatarService, SettingsService

logger = logging.getLogger(__name__)


class ProfileCallbackHandler(BaseCallbackHandler):
    """Хендлер для управления профилем пользователя."""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.user_service = UserService()
    
    @log_handler_call
    @user_required
    async def handle(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Показывает профиль пользователя."""
        user_id = query.from_user.id
        
        try:
            # Получаем данные профиля
            profile = await self.user_service.get_user_profile(user_id)
            if not profile:
                return CallbackResult.error_result("Профиль не найден")
            
            # Форматируем текст профиля
            profile_text = await self._format_profile_text(profile)
            
            # Создаем клавиатуру профиля
            keyboard = await create_user_profile_keyboard(user_id)
            
            await self.edit_safe_message(query.message, profile_text, keyboard)
            
            return CallbackResult.success_result(
                message="Профиль показан",
                answer_text="👤 Ваш профиль"
            )
            
        except Exception as e:
            logger.error(f"Ошибка показа профиля для user_id={user_id}: {e}", exc_info=True)
            return CallbackResult.error_result("Ошибка загрузки профиля")
    
    async def _format_profile_text(self, profile: dict) -> str:
        """Форматирует текст профиля."""
        name = profile.get('first_name', 'Пользователь')
        username = profile.get('username')
        
        text_parts = [
            f"👤 **Профиль: {name}**",
            ""
        ]
        
        if username:
            text_parts.append(f"🏷 Username: @{username}")
        
        text_parts.extend([
            f"🆔 ID: {profile['user_id']}",
            "",
            "💰 **Баланс:**",
            f"🍪 Печеньки: {profile['generations_left']}",
            f"🎭 Аватары: {profile['avatar_left']}",
            ""
        ])
        
        # Статистика
        if profile.get('payments_count', 0) > 0:
            text_parts.extend([
                "📊 **Статистика:**",
                f"💳 Покупок: {profile['payments_count']}",
                f"💰 Потрачено: {profile.get('total_spent', 0):.2f} RUB",
                ""
            ])
        
        # Email
        email = profile.get('email')
        if email:
            text_parts.append(f"📧 Email: {email}")
        else:
            text_parts.append("📧 Email: не указан")
        
        # Реферальная информация
        if profile.get('referrals_count', 0) > 0:
            text_parts.extend([
                "",
                f"👥 Приглашено друзей: {profile['referrals_count']}"
            ])
        
        return "\n".join(text_parts)


class AvatarCallbackHandler(BaseCallbackHandler):
    """Хендлер для управления аватарами."""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.avatar_service = AvatarService()
    
    @log_handler_call
    @user_required
    async def handle(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Обрабатывает callback'и управления аватарами."""
        user_id = query.from_user.id
        callback_data = query.data
        
        if callback_data == "my_avatars":
            return await self._show_avatars_list(query, user_id)
        elif callback_data.startswith("select_avatar_"):
            avatar_id = int(callback_data.replace("select_avatar_", ""))
            return await self._select_avatar(query, user_id, avatar_id)
        elif callback_data.startswith("delete_avatar_"):
            avatar_id = int(callback_data.replace("delete_avatar_", ""))
            return await self._confirm_delete_avatar(query, user_id, avatar_id)
        elif callback_data.startswith("confirm_delete_avatar_"):
            avatar_id = int(callback_data.replace("confirm_delete_avatar_", ""))
            return await self._delete_avatar(query, user_id, avatar_id)
        else:
            return CallbackResult.error_result("Неизвестная команда аватара")
    
    async def _show_avatars_list(self, query: CallbackQuery, user_id: int) -> CallbackResult:
        """Показывает список аватаров пользователя."""
        try:
            avatars = await self.avatar_service.get_user_avatars(user_id)
            active_avatar = await self.avatar_service.get_active_avatar(user_id)
            
            if not avatars:
                await self._show_no_avatars_message(query)
                return CallbackResult.success_result("Нет аватаров")
            
            # Форматируем список аватаров
            text = "🎭 **Мои аватары**\n\n"
            
            keyboard_buttons = []
            
            for avatar in avatars:
                avatar_name = self.avatar_service.get_avatar_display_name(avatar)
                status = self.avatar_service.format_avatar_status(avatar['status'])
                
                is_active = active_avatar and active_avatar['avatar_id'] == avatar['avatar_id']
                active_mark = " 🌟" if is_active else ""
                
                text += f"**{avatar_name}**{active_mark}\n"
                text += f"Status: {status}\n"
                if avatar.get('created_at'):
                    text += f"Создан: {avatar['created_at'][:10]}\n"
                text += "\n"
                
                # Кнопки для каждого аватара
                avatar_buttons = []
                
                if avatar['status'] == 'success' and not is_active:
                    avatar_buttons.append(
                        InlineKeyboardButton(
                            text=f"✅ Выбрать {avatar_name[:15]}",
                            callback_data=f"select_avatar_{avatar['avatar_id']}"
                        )
                    )
                
                avatar_buttons.append(
                    InlineKeyboardButton(
                        text=f"🗑 Удалить {avatar_name[:15]}",
                        callback_data=f"delete_avatar_{avatar['avatar_id']}"
                    )
                )
                
                keyboard_buttons.append(avatar_buttons)
            
            # Общие кнопки
            keyboard_buttons.extend([
                [InlineKeyboardButton(text="➕ Создать новый аватар", callback_data="create_avatar")],
                [InlineKeyboardButton(text="🔙 Назад в профиль", callback_data="profile")]
            ])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            await self.edit_safe_message(query.message, text.strip(), keyboard)
            
            return CallbackResult.success_result("Список аватаров показан")
            
        except Exception as e:
            logger.error(f"Ошибка показа аватаров для user_id={user_id}: {e}", exc_info=True)
            return CallbackResult.error_result("Ошибка загрузки аватаров")
    
    async def _show_no_avatars_message(self, query: CallbackQuery):
        """Показывает сообщение об отсутствии аватаров."""
        text = """
🎭 **Мои аватары**

У вас пока нет созданных аватаров.

Аватар позволяет генерировать фото с вашим лицом в разных стилях и ситуациях.

Для создания аватара нужно:
• 3-10 ваших фотографий
• 1 аватар из баланса
• 5-10 минут времени на обучение
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать аватар", callback_data="create_avatar")],
            [InlineKeyboardButton(text="🔙 Назад в профиль", callback_data="profile")]
        ])
        
        await self.edit_safe_message(query.message, text.strip(), keyboard)
    
    async def _select_avatar(self, query: CallbackQuery, user_id: int, avatar_id: int) -> CallbackResult:
        """Выбирает активный аватар."""
        try:
            success = await self.avatar_service.set_active_avatar(user_id, avatar_id)
            
            if success:
                text = f"""
✅ **Аватар активирован!**

Теперь вы можете использовать этот аватар для генерации фото с вашим лицом.

Перейдите в "Генерация" → "Фото с лицом" для создания изображений.
                """
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🎨 Генерировать фото", callback_data="generate_avatar")],
                    [InlineKeyboardButton(text="🎭 Мои аватары", callback_data="my_avatars")]
                ])
                
                await self.edit_safe_message(query.message, text.strip(), keyboard)
                
                return CallbackResult.success_result(
                    "Аватар активирован",
                    answer_text="✅ Аватар активирован!"
                )
            else:
                return CallbackResult.error_result("Не удалось активировать аватар")
                
        except Exception as e:
            logger.error(f"Ошибка активации аватара {avatar_id} для user_id={user_id}: {e}", exc_info=True)
            return CallbackResult.error_result(f"Ошибка активации: {e}")
    
    async def _confirm_delete_avatar(self, query: CallbackQuery, user_id: int, avatar_id: int) -> CallbackResult:
        """Запрашивает подтверждение удаления аватара."""
        try:
            avatars = await self.avatar_service.get_user_avatars(user_id)
            avatar = next((a for a in avatars if a['avatar_id'] == avatar_id), None)
            
            if not avatar:
                return CallbackResult.error_result("Аватар не найден")
            
            avatar_name = self.avatar_service.get_avatar_display_name(avatar)
            
            text = f"""
🗑 **Подтверждение удаления**

Вы действительно хотите удалить аватар "{avatar_name}"?

⚠️ **Внимание:** Это действие нельзя отменить!
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_avatar_{avatar_id}"),
                    InlineKeyboardButton(text="❌ Отмена", callback_data="my_avatars")
                ]
            ])
            
            await self.edit_safe_message(query.message, text.strip(), keyboard)
            
            return CallbackResult.success_result("Запрос подтверждения удаления")
            
        except Exception as e:
            logger.error(f"Ошибка запроса удаления аватара {avatar_id}: {e}", exc_info=True)
            return CallbackResult.error_result("Ошибка запроса удаления")
    
    async def _delete_avatar(self, query: CallbackQuery, user_id: int, avatar_id: int) -> CallbackResult:
        """Удаляет аватар."""
        try:
            success = await self.avatar_service.delete_avatar(user_id, avatar_id)
            
            if success:
                text = """
✅ **Аватар удален**

Аватар успешно удален из вашего профиля.
                """
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🎭 Мои аватары", callback_data="my_avatars")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
                ])
                
                await self.edit_safe_message(query.message, text.strip(), keyboard)
                
                return CallbackResult.success_result(
                    "Аватар удален",
                    answer_text="✅ Аватар удален"
                )
            else:
                return CallbackResult.error_result("Не удалось удалить аватар")
                
        except Exception as e:
            logger.error(f"Ошибка удаления аватара {avatar_id} для user_id={user_id}: {e}", exc_info=True)
            return CallbackResult.error_result(f"Ошибка удаления: {e}")


class SettingsCallbackHandler(BaseCallbackHandler):
    """Хендлер для управления настройками."""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.settings_service = SettingsService()
    
    @log_handler_call
    @user_required
    async def handle(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Обрабатывает callback'и настроек."""
        user_id = query.from_user.id
        callback_data = query.data
        
        if callback_data == "user_settings":
            return await self._show_settings(query, user_id)
        elif callback_data == "change_email":
            return await self._request_email_change(query, state)
        elif callback_data.startswith("toggle_"):
            setting_name = callback_data.replace("toggle_", "")
            return await self._toggle_setting(query, user_id, setting_name)
        else:
            return CallbackResult.error_result("Неизвестная команда настроек")
    
    async def _show_settings(self, query: CallbackQuery, user_id: int) -> CallbackResult:
        """Показывает настройки пользователя."""
        try:
            settings = await self.settings_service.get_user_settings(user_id)
            profile = await UserService().get_user_profile(user_id)
            
            text = "⚙️ **Настройки**\n\n"
            
            # Email
            email = profile.get('email') if profile else None
            if email:
                text += f"📧 Email: {email}\n"
            else:
                text += "📧 Email: не указан\n"
            
            text += "\n**Уведомления:**\n"
            
            # Настройки уведомлений
            notifications = "✅" if settings.get('notifications_enabled', True) else "❌"
            text += f"{notifications} Уведомления в боте\n"
            
            email_notifications = "✅" if settings.get('email_notifications', True) else "❌"
            text += f"{email_notifications} Email уведомления\n"
            
            text += "\n**Генерация:**\n"
            
            # Настройки генерации
            quality = settings.get('generation_quality', 'high')
            quality_text = {'low': 'Низкое', 'medium': 'Среднее', 'high': 'Высокое'}.get(quality, quality)
            text += f"🎨 Качество: {quality_text}\n"
            
            default_style = settings.get('default_style', 'realistic')
            text += f"🖼 Стиль по умолчанию: {default_style}\n"
            
            keyboard_buttons = [
                [InlineKeyboardButton(text="📧 Изменить email", callback_data="change_email")],
                [
                    InlineKeyboardButton(
                        text=f"{'🔕' if settings.get('notifications_enabled', True) else '🔔'} Уведомления",
                        callback_data="toggle_notifications_enabled"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=f"{'📧❌' if settings.get('email_notifications', True) else '📧✅'} Email уведомления",
                        callback_data="toggle_email_notifications"
                    )
                ],
                [InlineKeyboardButton(text="🔙 Назад в профиль", callback_data="profile")]
            ]
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            await self.edit_safe_message(query.message, text, keyboard)
            
            return CallbackResult.success_result("Настройки показаны")
            
        except Exception as e:
            logger.error(f"Ошибка показа настроек для user_id={user_id}: {e}", exc_info=True)
            return CallbackResult.error_result("Ошибка загрузки настроек")
    
    async def _request_email_change(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Запрашивает изменение email."""
        text = """
📧 **Изменение email**

Введите новый email адрес:

Email используется для:
• Отправки чеков об оплате
• Уведомлений о готовности аватаров
• Важных обновлений сервиса
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="user_settings")]
        ])
        
        await self.edit_safe_message(query.message, text.strip(), keyboard)
        await state.set_state(BotStates.AWAITING_EMAIL_CHANGE)
        
        return CallbackResult.success_result("Запрос изменения email")
    
    async def _toggle_setting(self, query: CallbackQuery, user_id: int, setting_name: str) -> CallbackResult:
        """Переключает настройку."""
        try:
            current_settings = await self.settings_service.get_user_settings(user_id)
            
            # Переключаем настройку
            current_value = current_settings.get(setting_name, True)
            new_settings = {setting_name: not current_value}
            
            success = await self.settings_service.update_user_settings(user_id, new_settings)
            
            if success:
                # Обновляем отображение настроек
                return await self._show_settings(query, user_id)
            else:
                return CallbackResult.error_result("Не удалось обновить настройку")
                
        except Exception as e:
            logger.error(f"Ошибка переключения настройки {setting_name} для user_id={user_id}: {e}", exc_info=True)
            return CallbackResult.error_result("Ошибка обновления настройки")