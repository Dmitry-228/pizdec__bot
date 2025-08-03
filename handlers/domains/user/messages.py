"""
Message хендлеры пользовательского домена.
"""

import logging
import re
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from keyboards import create_main_menu_keyboard
from states import BotStates
from ..common.base import BaseMessageHandler
from ..common.decorators import log_handler_call, user_required
from ..common.types import HandlerResult
from .services import UserService, SettingsService

logger = logging.getLogger(__name__)


class EmailChangeHandler(BaseMessageHandler):
    """Хендлер для изменения email пользователя."""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.user_service = UserService()
        self.settings_service = SettingsService()
    
    @log_handler_call
    @user_required
    async def handle(self, message: Message, state: FSMContext) -> HandlerResult:
        """Обрабатывает ввод нового email."""
        user_id = message.from_user.id
        email = message.text.strip()
        
        # Валидация email
        if not self._is_valid_email(email):
            await self._send_invalid_email_message(message)
            return HandlerResult.success_result("Неверный формат email")
        
        try:
            # Проверяем, не используется ли уже этот email
            existing_user = await self.user_service.get_user_by_email(email)
            if existing_user and existing_user['user_id'] != user_id:
                await self._send_email_taken_message(message)
                return HandlerResult.success_result("Email уже используется")
            
            # Обновляем email
            success = await self.user_service.update_user_email(user_id, email)
            
            if success:
                await self._send_email_updated_message(message, email)
                await state.clear()
                return HandlerResult.success_result(f"Email обновлен: {email}")
            else:
                await self._send_email_update_error_message(message)
                return HandlerResult.error_result("Ошибка обновления email")
                
        except Exception as e:
            logger.error(f"Ошибка обновления email для user_id={user_id}: {e}", exc_info=True)
            await self._send_email_update_error_message(message)
            return HandlerResult.error_result(f"Ошибка обновления email: {e}")
    
    def _is_valid_email(self, email: str) -> bool:
        """Проверяет валидность email."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    async def _send_invalid_email_message(self, message: Message):
        """Отправляет сообщение о неверном формате email."""
        text = """
❌ **Неверный формат email**

Пожалуйста, введите корректный email адрес.

Пример: user@example.com
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="user_settings")]
        ])
        
        await message.answer(text.strip(), reply_markup=keyboard)
    
    async def _send_email_taken_message(self, message: Message):
        """Отправляет сообщение о том, что email уже используется."""
        text = """
⚠️ **Email уже используется**

Этот email адрес уже привязан к другому аккаунту.

Пожалуйста, введите другой email или обратитесь в поддержку.
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="user_settings")]
        ])
        
        await message.answer(text.strip(), reply_markup=keyboard)
    
    async def _send_email_updated_message(self, message: Message, email: str):
        """Отправляет сообщение об успешном обновлении email."""
        text = f"""
✅ **Email обновлен**

Ваш новый email: {email}

Теперь на этот адрес будут приходить:
• Чеки об оплате
• Уведомления о готовности аватаров
• Важные обновления сервиса
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data="user_settings")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await message.answer(text.strip(), reply_markup=keyboard)
    
    async def _send_email_update_error_message(self, message: Message):
        """Отправляет сообщение об ошибке обновления email."""
        text = """
❌ **Ошибка обновления email**

Произошла ошибка при сохранении нового email.

Попробуйте еще раз или обратитесь в поддержку.
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data="user_settings")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await message.answer(text.strip(), reply_markup=keyboard)


class AvatarPhotosHandler(BaseMessageHandler):
    """Хендлер для загрузки фотографий для создания аватара."""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.user_service = UserService()
    
    @log_handler_call
    @user_required
    async def handle(self, message: Message, state: FSMContext) -> HandlerResult:
        """Обрабатывает загрузку фотографий для аватара."""
        user_id = message.from_user.id
        
        # Проверяем состояние
        current_state = await state.get_state()
        if current_state != BotStates.UPLOADING_AVATAR_PHOTOS:
            return HandlerResult.success_result("Неактивное состояние загрузки")
        
        # Проверяем, что это фото
        if not message.photo:
            await self._send_photo_required_message(message)
            return HandlerResult.success_result("Требуется фото")
        
        try:
            # Получаем данные состояния
            state_data = await state.get_data()
            uploaded_photos = state_data.get('uploaded_photos', [])
            avatar_name = state_data.get('avatar_name', 'Мой аватар')
            
            # Получаем файл фото
            photo = message.photo[-1]  # Берем самое большое разрешение
            file_info = await self.bot.get_file(photo.file_id)
            
            # Сохраняем информацию о фото
            photo_info = {
                'file_id': photo.file_id,
                'file_unique_id': photo.file_unique_id,
                'file_path': file_info.file_path,
                'file_size': photo.file_size,
                'width': photo.width,
                'height': photo.height
            }
            
            uploaded_photos.append(photo_info)
            
            # Обновляем состояние
            await state.update_data(uploaded_photos=uploaded_photos)
            
            photos_count = len(uploaded_photos)
            
            if photos_count < 3:
                # Нужно еще фото
                await self._send_need_more_photos_message(message, photos_count)
                return HandlerResult.success_result(f"Загружено {photos_count} фото")
            
            elif photos_count < 10:
                # Можно создать аватар или загрузить еще
                await self._send_can_create_avatar_message(message, photos_count, avatar_name)
                return HandlerResult.success_result(f"Загружено {photos_count} фото, можно создать")
            
            else:
                # Максимум фото достигнут
                await self._send_max_photos_reached_message(message, avatar_name)
                return HandlerResult.success_result("Максимум фото достигнут")
                
        except Exception as e:
            logger.error(f"Ошибка загрузки фото аватара для user_id={user_id}: {e}", exc_info=True)
            await self._send_photo_upload_error_message(message)
            return HandlerResult.error_result(f"Ошибка загрузки фото: {e}")
    
    async def _send_photo_required_message(self, message: Message):
        """Отправляет сообщение о необходимости фото."""
        text = """
📷 **Нужно фото**

Пожалуйста, отправьте фотографию для создания аватара.

Требования к фото:
• Ваше лицо должно быть хорошо видно
• Качественное освещение
• Без очков и головных уборов (желательно)
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить создание", callback_data="profile")]
        ])
        
        await message.answer(text.strip(), reply_markup=keyboard)
    
    async def _send_need_more_photos_message(self, message: Message, count: int):
        """Отправляет сообщение о необходимости еще фото."""
        remaining = 3 - count
        
        text = f"""
📷 **Фото {count}/10 загружено**

Отлично! Загрузите еще минимум {remaining} фото для создания качественного аватара.

💡 **Советы:**
• Разные ракурсы и выражения лица
• Хорошее освещение
• Четкие фото без размытия
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить создание", callback_data="profile")]
        ])
        
        await message.answer(text.strip(), reply_markup=keyboard)
    
    async def _send_can_create_avatar_message(self, message: Message, count: int, avatar_name: str):
        """Отправляет сообщение о возможности создания аватара."""
        text = f"""
📷 **Фото {count}/10 загружено**

Отлично! У вас достаточно фото для создания аватара "{avatar_name}".

Вы можете:
• Создать аватар сейчас
• Загрузить еще фото (до 10 максимум)
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Создать аватар", callback_data="confirm_create_avatar")],
            [InlineKeyboardButton(text="📷 Загрузить еще фото", callback_data="continue_upload")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="profile")]
        ])
        
        await message.answer(text.strip(), reply_markup=keyboard)
    
    async def _send_max_photos_reached_message(self, message: Message, avatar_name: str):
        """Отправляет сообщение о достижении максимума фото."""
        text = f"""
📷 **Максимум фото загружено (10/10)**

Отлично! Вы загрузили максимальное количество фото для аватара "{avatar_name}".

Теперь можно создать аватар.
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Создать аватар", callback_data="confirm_create_avatar")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="profile")]
        ])
        
        await message.answer(text.strip(), reply_markup=keyboard)
    
    async def _send_photo_upload_error_message(self, message: Message):
        """Отправляет сообщение об ошибке загрузки фото."""
        text = """
❌ **Ошибка загрузки фото**

Произошла ошибка при обработке фотографии.

Попробуйте загрузить другое фото или обратитесь в поддержку.
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать еще раз", callback_data="continue_upload")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="profile")]
        ])
        
        await message.answer(text.strip(), reply_markup=keyboard)


class FeedbackHandler(BaseMessageHandler):
    """Хендлер для обратной связи от пользователей."""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.user_service = UserService()
    
    @log_handler_call
    @user_required
    async def handle(self, message: Message, state: FSMContext) -> HandlerResult:
        """Обрабатывает отправку обратной связи."""
        user_id = message.from_user.id
        
        # Проверяем состояние
        current_state = await state.get_state()
        if current_state != BotStates.AWAITING_FEEDBACK:
            return HandlerResult.success_result("Неактивное состояние обратной связи")
        
        feedback_text = message.text.strip()
        
        if not feedback_text:
            await self._send_empty_feedback_message(message)
            return HandlerResult.success_result("Пустое сообщение")
        
        try:
            # Сохраняем обратную связь
            success = await self.user_service.save_user_feedback(
                user_id=user_id,
                feedback_text=feedback_text,
                message_id=message.message_id
            )
            
            if success:
                await self._send_feedback_saved_message(message)
                await state.clear()
                
                # Уведомляем администраторов (если нужно)
                await self._notify_admins_about_feedback(user_id, feedback_text)
                
                return HandlerResult.success_result("Обратная связь сохранена")
            else:
                await self._send_feedback_error_message(message)
                return HandlerResult.error_result("Ошибка сохранения обратной связи")
                
        except Exception as e:
            logger.error(f"Ошибка сохранения обратной связи от user_id={user_id}: {e}", exc_info=True)
            await self._send_feedback_error_message(message)
            return HandlerResult.error_result(f"Ошибка обратной связи: {e}")
    
    async def _send_empty_feedback_message(self, message: Message):
        """Отправляет сообщение о пустом сообщении."""
        text = """
📝 **Напишите ваше сообщение**

Пожалуйста, опишите вашу проблему, предложение или вопрос.

Мы внимательно рассмотрим ваше обращение.
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="main_menu")]
        ])
        
        await message.answer(text.strip(), reply_markup=keyboard)
    
    async def _send_feedback_saved_message(self, message: Message):
        """Отправляет сообщение об успешном сохранении обратной связи."""
        text = """
✅ **Спасибо за обратную связь!**

Ваше сообщение получено и будет рассмотрено в ближайшее время.

Мы стараемся отвечать на все обращения в течение 24 часов.
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await message.answer(text.strip(), reply_markup=keyboard)
    
    async def _send_feedback_error_message(self, message: Message):
        """Отправляет сообщение об ошибке сохранения обратной связи."""
        text = """
❌ **Ошибка отправки сообщения**

Произошла ошибка при сохранении вашего сообщения.

Попробуйте еще раз или обратитесь в поддержку напрямую.
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать еще раз", callback_data="send_feedback")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await message.answer(text.strip(), reply_markup=keyboard)
    
    async def _notify_admins_about_feedback(self, user_id: int, feedback_text: str):
        """Уведомляет администраторов о новой обратной связи."""
        try:
            # Получаем список администраторов
            admins = await self.user_service.get_admin_users()
            
            if not admins:
                return
            
            # Получаем информацию о пользователе
            user_info = await self.user_service.get_user_profile(user_id)
            user_name = user_info.get('first_name', 'Пользователь') if user_info else 'Пользователь'
            username = user_info.get('username') if user_info else None
            
            # Формируем сообщение для админов
            admin_text = f"""
📝 **Новая обратная связь**

👤 От: {user_name}
🆔 ID: {user_id}
"""
            
            if username:
                admin_text += f"🏷 Username: @{username}\n"
            
            admin_text += f"""

💬 **Сообщение:**
{feedback_text}
            """
            
            # Отправляем уведомления админам
            for admin in admins:
                try:
                    await self.bot.send_message(
                        chat_id=admin['user_id'],
                        text=admin_text.strip()
                    )
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления админу {admin['user_id']}: {e}")
                    
        except Exception as e:
            logger.error(f"Ошибка уведомления админов о обратной связи: {e}", exc_info=True)