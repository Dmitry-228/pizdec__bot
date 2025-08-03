"""
Основной хендлер пользовательского домена.
"""

import logging
from typing import Dict, Any
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from states import BotStates
from ..common.base import BaseDomainHandler
from ..common.types import HandlerResult, CallbackResult
from .callbacks import ProfileCallbackHandler, AvatarCallbackHandler, SettingsCallbackHandler
from .messages import EmailChangeHandler, AvatarPhotosHandler, FeedbackHandler

logger = logging.getLogger(__name__)


class UserDomainHandler(BaseDomainHandler):
    """
    Основной хендлер пользовательского домена.
    
    Управляет:
    - Профилем пользователя
    - Аватарами
    - Настройками
    - Обратной связью
    """
    
    def __init__(self, bot):
        super().__init__(bot)
        self.domain_name = "user"
        
        # Инициализируем callback хендлеры
        self.profile_handler = ProfileCallbackHandler(bot)
        self.avatar_handler = AvatarCallbackHandler(bot)
        self.settings_handler = SettingsCallbackHandler(bot)
        
        # Инициализируем message хендлеры
        self.email_change_handler = EmailChangeHandler(bot)
        self.avatar_photos_handler = AvatarPhotosHandler(bot)
        self.feedback_handler = FeedbackHandler(bot)
        
        # Маппинг callback'ов на хендлеры
        self.callback_routes = {
            # Профиль
            'profile': self.profile_handler,
            
            # Аватары
            'my_avatars': self.avatar_handler,
            'select_avatar_': self.avatar_handler,  # Префикс
            'delete_avatar_': self.avatar_handler,  # Префикс
            'confirm_delete_avatar_': self.avatar_handler,  # Префикс
            'create_avatar': self._handle_create_avatar_callback,
            'confirm_create_avatar': self._handle_confirm_create_avatar,
            'continue_upload': self._handle_continue_upload,
            
            # Настройки
            'user_settings': self.settings_handler,
            'change_email': self.settings_handler,
            'toggle_': self.settings_handler,  # Префикс
            
            # Обратная связь
            'send_feedback': self._handle_send_feedback_callback,
        }
        
        # Маппинг состояний на message хендлеры
        self.message_state_routes = {
            BotStates.AWAITING_EMAIL_CHANGE: self.email_change_handler,
            BotStates.UPLOADING_AVATAR_PHOTOS: self.avatar_photos_handler,
            BotStates.AWAITING_FEEDBACK: self.feedback_handler,
        }
    
    async def handle_callback(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Обрабатывает callback запросы пользовательского домена."""
        callback_data = query.data
        
        try:
            # Ищем точное совпадение
            if callback_data in self.callback_routes:
                handler = self.callback_routes[callback_data]
                if callable(handler):
                    return await handler(query, state)
                else:
                    return await handler.handle(query, state)
            
            # Ищем по префиксам
            for prefix, handler in self.callback_routes.items():
                if callback_data.startswith(prefix):
                    if callable(handler):
                        return await handler(query, state)
                    else:
                        return await handler.handle(query, state)
            
            logger.warning(f"Неизвестный callback в user домене: {callback_data}")
            return CallbackResult.error_result(f"Неизвестная команда: {callback_data}")
            
        except Exception as e:
            logger.error(f"Ошибка обработки callback {callback_data}: {e}", exc_info=True)
            return CallbackResult.error_result(f"Ошибка обработки: {e}")
    
    async def handle_message(self, message: Message, state: FSMContext) -> HandlerResult:
        """Обрабатывает сообщения пользовательского домена."""
        current_state = await state.get_state()
        
        try:
            # Проверяем состояние и направляем к соответствующему хендлеру
            if current_state in self.message_state_routes:
                handler = self.message_state_routes[current_state]
                return await handler.handle(message, state)
            
            # Если состояние не найдено, возвращаем успех без обработки
            return HandlerResult.success_result("Сообщение не обработано в user домене")
            
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения в user домене: {e}", exc_info=True)
            return HandlerResult.error_result(f"Ошибка обработки сообщения: {e}")
    
    async def _handle_create_avatar_callback(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Обрабатывает начало создания аватара."""
        from keyboards import create_main_menu_keyboard
        from ..generation.services import GenerationService
        
        user_id = query.from_user.id
        
        try:
            # Проверяем баланс аватаров
            generation_service = GenerationService()
            user_resources = await generation_service.get_user_resources(user_id)
            
            if user_resources['avatar_left'] <= 0:
                text = """
❌ **Недостаточно аватаров**

Для создания аватара нужен 1 аватар из баланса.

Купите тариф с аватарами или дождитесь пополнения баланса.
                """
                
                keyboard = create_main_menu_keyboard()
                await query.message.edit_text(text.strip(), reply_markup=keyboard)
                
                return CallbackResult.success_result(
                    "Недостаточно аватаров",
                    answer_text="❌ Недостаточно аватаров"
                )
            
            # Запрашиваем название аватара
            text = """
🎭 **Создание аватара**

Как назовем ваш новый аватар?

Например: "Рабочий", "Для соцсетей", "Официальный"

Введите название:
            """
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Отмена", callback_data="profile")]
            ])
            
            await query.message.edit_text(text.strip(), reply_markup=keyboard)
            await state.set_state(BotStates.AWAITING_AVATAR_NAME)
            
            return CallbackResult.success_result("Запрос названия аватара")
            
        except Exception as e:
            logger.error(f"Ошибка начала создания аватара для user_id={user_id}: {e}", exc_info=True)
            return CallbackResult.error_result(f"Ошибка создания аватара: {e}")
    
    async def _handle_confirm_create_avatar(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Подтверждает создание аватара."""
        from ..generation.services import GenerationService
        
        user_id = query.from_user.id
        
        try:
            # Получаем данные из состояния
            state_data = await state.get_data()
            uploaded_photos = state_data.get('uploaded_photos', [])
            avatar_name = state_data.get('avatar_name', 'Мой аватар')
            
            if len(uploaded_photos) < 3:
                return CallbackResult.error_result("Недостаточно фотографий")
            
            # Создаем аватар
            generation_service = GenerationService()
            avatar_id = await generation_service.create_avatar(
                user_id=user_id,
                avatar_name=avatar_name,
                photos=uploaded_photos
            )
            
            if avatar_id:
                text = f"""
✅ **Аватар "{avatar_name}" создается!**

🔄 Процесс обучения займет 5-10 минут.

Мы уведомим вас, когда аватар будет готов к использованию.

📱 Уведомление придет в бот
📧 Также отправим на email (если указан)
                """
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🎭 Мои аватары", callback_data="my_avatars")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
                ])
                
                await query.message.edit_text(text.strip(), reply_markup=keyboard)
                await state.clear()
                
                return CallbackResult.success_result(
                    f"Аватар {avatar_name} создается",
                    answer_text="✅ Аватар создается!"
                )
            else:
                return CallbackResult.error_result("Ошибка создания аватара")
                
        except Exception as e:
            logger.error(f"Ошибка подтверждения создания аватара для user_id={user_id}: {e}", exc_info=True)
            return CallbackResult.error_result(f"Ошибка создания: {e}")
    
    async def _handle_continue_upload(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Продолжает загрузку фотографий."""
        text = """
📷 **Продолжайте загрузку фото**

Отправьте еще фотографии для создания качественного аватара.

Максимум: 10 фото
Минимум: 3 фото
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить создание", callback_data="profile")]
        ])
        
        await query.message.edit_text(text.strip(), reply_markup=keyboard)
        
        return CallbackResult.success_result("Продолжение загрузки фото")
    
    async def _handle_send_feedback_callback(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Обрабатывает запрос на отправку обратной связи."""
        text = """
📝 **Обратная связь**

Напишите ваше сообщение, предложение или вопрос.

Мы внимательно рассмотрим ваше обращение и постараемся ответить в течение 24 часов.

Введите ваше сообщение:
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="main_menu")]
        ])
        
        await query.message.edit_text(text.strip(), reply_markup=keyboard)
        await state.set_state(BotStates.AWAITING_FEEDBACK)
        
        return CallbackResult.success_result("Запрос обратной связи")
    
    def get_domain_info(self) -> Dict[str, Any]:
        """Возвращает информацию о домене."""
        return {
            'name': self.domain_name,
            'description': 'Управление профилем, аватарами и настройками пользователя',
            'callback_routes': list(self.callback_routes.keys()),
            'message_states': list(self.message_state_routes.keys()),
            'handlers': {
                'callbacks': [
                    'ProfileCallbackHandler',
                    'AvatarCallbackHandler', 
                    'SettingsCallbackHandler'
                ],
                'messages': [
                    'EmailChangeHandler',
                    'AvatarPhotosHandler',
                    'FeedbackHandler'
                ]
            }
        }
