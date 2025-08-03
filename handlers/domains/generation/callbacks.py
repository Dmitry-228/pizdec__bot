"""
Callback хендлеры домена генерации.
"""

import logging
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from database import get_active_trainedmodel
from keyboards import create_main_menu_keyboard, create_generation_keyboard
from states import BotStates
from ..common.base import BaseCallbackHandler
from ..common.decorators import log_handler_call, user_required, check_resources
from ..common.types import CallbackResult, GenerationRequest
from .services import GenerationService, StyleService

logger = logging.getLogger(__name__)


class GenerationMenuCallbackHandler(BaseCallbackHandler):
    """Хендлер для главного меню генерации."""
    
    @log_handler_call
    @user_required
    async def handle(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Показывает меню генерации."""
        user_id = query.from_user.id
        
        try:
            menu_text = """
🎨 **Меню генерации**

Выберите тип контента, который хотите создать:

📸 **Фото по тексту** - создание изображений по описанию
🎭 **Фото с лицом** - генерация с вашим аватаром  
🎬 **Видео** - создание коротких видео
👤 **Создать аватар** - обучение на ваших фото
            """
            
            keyboard = await create_generation_keyboard(user_id)
            await self.edit_safe_message(query.message, menu_text.strip(), keyboard)
            
            return CallbackResult.success_result(
                message="Меню генерации показано",
                answer_text="🎨 Выберите тип генерации"
            )
            
        except Exception as e:
            logger.error(f"Ошибка показа меню генерации для user_id={user_id}: {e}", exc_info=True)
            return CallbackResult.error_result("Ошибка загрузки меню")


class PhotoGenerationCallbackHandler(BaseCallbackHandler):
    """Хендлер для генерации фото по тексту."""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.style_service = StyleService()
    
    @log_handler_call
    @user_required
    @check_resources(photos=1)
    async def handle(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Обрабатывает запрос на генерацию фото по тексту."""
        user_id = query.from_user.id
        
        try:
            # Сохраняем тип генерации в состоянии
            await state.update_data(
                generation_type='photo',
                generation_subtype='text_to_image'
            )
            
            # Показываем доступные стили
            await self._show_style_selection(query, 'photo')
            await state.set_state(BotStates.AWAITING_STYLE_SELECTION)
            
            return CallbackResult.success_result(
                message="Запрос на генерацию фото по тексту",
                answer_text="📸 Выберите стиль для фото"
            )
            
        except Exception as e:
            logger.error(f"Ошибка запроса генерации фото для user_id={user_id}: {e}", exc_info=True)
            return CallbackResult.error_result("Ошибка запроса генерации")
    
    async def _show_style_selection(self, query: CallbackQuery, generation_type: str):
        """Показывает выбор стилей."""
        styles = self.style_service.get_available_styles(generation_type)
        
        text = f"""
🎨 **Выбор стиля для {generation_type}**

Выберите стиль генерации:
        """
        
        keyboard_buttons = []
        for style_key, style_data in styles.items():
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"{style_data['name']} - {style_data['description']}", 
                    callback_data=f"style_{style_key}"
                )
            ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="🔙 Назад", callback_data="generation_menu")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        await self.edit_safe_message(query.message, text.strip(), keyboard)


class AvatarGenerationCallbackHandler(BaseCallbackHandler):
    """Хендлер для генерации фото с аватаром."""
    
    @log_handler_call
    @user_required
    @check_resources(photos=1)
    async def handle(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Обрабатывает запрос на генерацию фото с аватаром."""
        user_id = query.from_user.id
        
        try:
            # Проверяем наличие активного аватара
            active_avatar = await get_active_trainedmodel(user_id)
            if not active_avatar or active_avatar[3] != 'success':
                await self._show_no_avatar_message(query)
                return CallbackResult.error_result("Нет активного аватара")
            
            # Сохраняем тип генерации в состоянии
            await state.update_data(
                generation_type='photo',
                generation_subtype='with_avatar',
                active_avatar_id=active_avatar[0]
            )
            
            # Показываем доступные стили
            style_service = StyleService()
            await self._show_avatar_style_selection(query, style_service)
            await state.set_state(BotStates.AWAITING_STYLE_SELECTION)
            
            return CallbackResult.success_result(
                message="Запрос на генерацию фото с аватаром",
                answer_text="🎭 Выберите стиль для фото с аватаром"
            )
            
        except Exception as e:
            logger.error(f"Ошибка запроса генерации с аватаром для user_id={user_id}: {e}", exc_info=True)
            return CallbackResult.error_result("Ошибка запроса генерации")
    
    async def _show_no_avatar_message(self, query: CallbackQuery):
        """Показывает сообщение об отсутствии аватара."""
        text = """
❌ **Нет активного аватара**

Для генерации фото с лицом нужно сначала создать аватар.

Перейдите в "Личный кабинет" → "Мои аватары" и создайте новый аватар или активируйте существующий.
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👤 Создать аватар", callback_data="create_avatar")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await self.edit_safe_message(query.message, text.strip(), keyboard)
    
    async def _show_avatar_style_selection(self, query: CallbackQuery, style_service: StyleService):
        """Показывает выбор стилей для аватара."""
        styles = style_service.get_available_styles('photo')
        
        text = """
🎭 **Выбор стиля для фото с аватаром**

Ваш аватар будет использован для генерации фото в выбранном стиле:
        """
        
        keyboard_buttons = []
        for style_key, style_data in styles.items():
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"{style_data['name']} - {style_data['description']}", 
                    callback_data=f"style_{style_key}"
                )
            ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="🔙 Назад", callback_data="generation_menu")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        await self.edit_safe_message(query.message, text.strip(), keyboard)


class VideoGenerationCallbackHandler(BaseCallbackHandler):
    """Хендлер для генерации видео."""
    
    @log_handler_call
    @user_required
    @check_resources(photos=1)  # Видео тоже тратит печеньки
    async def handle(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Обрабатывает запрос на генерацию видео."""
        user_id = query.from_user.id
        
        try:
            # Сохраняем тип генерации в состоянии
            await state.update_data(
                generation_type='video'
            )
            
            # Показываем доступные стили для видео
            style_service = StyleService()
            await self._show_video_style_selection(query, style_service)
            await state.set_state(BotStates.AWAITING_STYLE_SELECTION)
            
            return CallbackResult.success_result(
                message="Запрос на генерацию видео",
                answer_text="🎬 Выберите стиль для видео"
            )
            
        except Exception as e:
            logger.error(f"Ошибка запроса генерации видео для user_id={user_id}: {e}", exc_info=True)
            return CallbackResult.error_result("Ошибка запроса генерации")
    
    async def _show_video_style_selection(self, query: CallbackQuery, style_service: StyleService):
        """Показывает выбор стилей для видео."""
        styles = style_service.get_available_styles('video')
        
        text = """
🎬 **Выбор стиля для видео**

Выберите стиль для генерации видео:
        """
        
        keyboard_buttons = []
        for style_key, style_data in styles.items():
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"{style_data['name']} - {style_data['description']}", 
                    callback_data=f"style_{style_key}"
                )
            ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="🔙 Назад", callback_data="generation_menu")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        await self.edit_safe_message(query.message, text.strip(), keyboard)


class StyleCallbackHandler(BaseCallbackHandler):
    """Хендлер для выбора стиля генерации."""
    
    @log_handler_call
    async def handle(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Обрабатывает выбор стиля."""
        user_id = query.from_user.id
        callback_data = query.data
        
        # Извлекаем стиль из callback_data
        style_key = callback_data.replace("style_", "")
        
        try:
            # Сохраняем выбранный стиль
            await state.update_data(selected_style=style_key)
            
            # Получаем данные о типе генерации
            user_data = await state.get_data()
            generation_type = user_data.get('generation_type', 'photo')
            
            if generation_type == 'video':
                # Для видео сразу запрашиваем промпт
                await self._request_video_prompt(query)
                await state.set_state(BotStates.AWAITING_PROMPT)
            else:
                # Для фото запрашиваем промпт
                await self._request_photo_prompt(query, style_key)
                await state.set_state(BotStates.AWAITING_PROMPT)
            
            return CallbackResult.success_result(
                message=f"Выбран стиль {style_key}",
                answer_text=f"🎨 Стиль выбран: {style_key}"
            )
            
        except Exception as e:
            logger.error(f"Ошибка выбора стиля для user_id={user_id}: {e}", exc_info=True)
            return CallbackResult.error_result("Ошибка выбора стиля")
    
    async def _request_photo_prompt(self, query: CallbackQuery, style_key: str):
        """Запрашивает промпт для генерации фото."""
        text = f"""
✏️ **Опишите желаемое изображение**

Стиль: {style_key}

Напишите подробное описание того, что вы хотите увидеть на фото. Чем детальнее описание, тем лучше результат!

Примеры:
• "Кот в космическом шлеме на фоне звезд"
• "Закат над океаном с парусником"
• "Девушка в красном платье в парке"
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Изменить стиль", callback_data="generate_photo")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await self.edit_safe_message(query.message, text.strip(), keyboard)
    
    async def _request_video_prompt(self, query: CallbackQuery):
        """Запрашивает промпт для генерации видео."""
        text = """
🎬 **Опишите желаемое видео**

Напишите описание сцены для видео. Видео будет длиться 3-5 секунд.

Примеры:
• "Волны разбиваются о скалы"
• "Огонь в камине"
• "Падающие листья в осеннем лесу"
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Изменить стиль", callback_data="generate_video")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await self.edit_safe_message(query.message, text.strip(), keyboard)


class CreateAvatarCallbackHandler(BaseCallbackHandler):
    """Хендлер для создания аватара."""
    
    @log_handler_call
    @user_required
    @check_resources(avatars=1)
    async def handle(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Обрабатывает запрос на создание аватара."""
        user_id = query.from_user.id
        
        try:
            # Сохраняем тип генерации в состоянии
            await state.update_data(generation_type='avatar')
            
            # Запрашиваем фото для аватара
            await self._request_avatar_photos(query)
            await state.set_state(BotStates.AWAITING_FACE_IMAGE)
            
            return CallbackResult.success_result(
                message="Запрос на создание аватара",
                answer_text="👤 Отправьте фото для аватара"
            )
            
        except Exception as e:
            logger.error(f"Ошибка запроса создания аватара для user_id={user_id}: {e}", exc_info=True)
            return CallbackResult.error_result("Ошибка запроса создания аватара")
    
    async def _request_avatar_photos(self, query: CallbackQuery):
        """Запрашивает фото для создания аватара."""
        text = """
📸 **Создание аватара**

Отправьте 3-10 фотографий себя для обучения аватара:

✅ **Хорошие фото:**
• Четкие фото лица
• Разные ракурсы и выражения
• Хорошее освещение
• Только вы на фото

❌ **Плохие фото:**
• Размытые или темные
• Несколько людей на фото
• Очки или маски
• Слишком далеко от камеры

Отправьте первое фото:
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="generation_menu")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await self.edit_safe_message(query.message, text.strip(), keyboard)