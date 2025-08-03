"""
Message хендлеры домена генерации.
"""

import logging
import os
from typing import List
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from states import BotStates
from keyboards import create_main_menu_keyboard
from ..common.base import BaseMessageHandler
from ..common.decorators import log_handler_call, user_required, check_resources
from ..common.types import HandlerResult, GenerationRequest
from .services import GenerationService, StyleService

logger = logging.getLogger(__name__)


class PromptMessageHandler(BaseMessageHandler):
    """Хендлер для обработки промптов (текстовых описаний)."""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.generation_service = GenerationService()
        self.style_service = StyleService()
    
    @log_handler_call
    @user_required
    async def handle(self, message: Message, state: FSMContext) -> HandlerResult:
        """Обрабатывает текстовый промпт для генерации."""
        user_id = message.from_user.id
        prompt = message.text.strip()
        
        if not prompt:
            await self._send_empty_prompt_error(message)
            return HandlerResult.error_result("Пустой промпт")
        
        try:
            # Получаем данные из состояния
            user_data = await state.get_data()
            generation_type = user_data.get('generation_type', 'photo')
            selected_style = user_data.get('selected_style', 'realistic')
            generation_subtype = user_data.get('generation_subtype', 'text_to_image')
            
            # Создаем запрос на генерацию
            generation_request = GenerationRequest(
                user_id=user_id,
                generation_type=generation_type,
                prompt=prompt,
                style=selected_style,
                additional_params={
                    'generation_subtype': generation_subtype,
                    'active_avatar_id': user_data.get('active_avatar_id')
                }
            )
            
            # Отправляем сообщение о начале генерации
            await self._send_generation_started(message, generation_type, selected_style)
            
            # Выполняем генерацию
            if generation_type == 'photo':
                result = await self.generation_service.generate_photo(generation_request)
            elif generation_type == 'video':
                result = await self.generation_service.generate_video(generation_request)
            else:
                return HandlerResult.error_result("Неизвестный тип генерации")
            
            # Отправляем результат пользователю
            await self._send_generation_result(message, result, generation_type)
            
            # Очищаем состояние
            await state.clear()
            
            logger.info(f"Генерация завершена для user_id={user_id}, type={generation_type}, style={selected_style}")
            
            return HandlerResult.success_result(
                message="Генерация завершена",
                data={
                    "user_id": user_id,
                    "generation_type": generation_type,
                    "style": selected_style,
                    "prompt": prompt,
                    "result": result
                }
            )
            
        except Exception as e:
            logger.error(f"Ошибка генерации для user_id={user_id}: {e}", exc_info=True)
            await self._send_generation_error(message)
            return HandlerResult.error_result(f"Ошибка генерации: {e}")
    
    async def _send_empty_prompt_error(self, message: Message):
        """Отправляет сообщение об ошибке пустого промпта."""
        error_text = """
❌ **Пустое описание**

Пожалуйста, напишите описание того, что вы хотите сгенерировать.

Пример: "Кот в космическом шлеме на фоне звезд"
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎨 Меню генерации", callback_data="generation_menu")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await self.send_safe_message(message.from_user.id, error_text.strip(), keyboard)
    
    async def _send_generation_started(self, message: Message, generation_type: str, style: str):
        """Отправляет сообщение о начале генерации."""
        type_emoji = "📸" if generation_type == "photo" else "🎬"
        type_name = "фото" if generation_type == "photo" else "видео"
        
        text = f"""
{type_emoji} **Генерация {type_name} началась!**

🎨 Стиль: {style}
⏱️ Примерное время: 30-60 секунд

Пожалуйста, подождите...
        """
        
        await self.send_safe_message(message.from_user.id, text.strip())
    
    async def _send_generation_result(self, message: Message, result: dict, generation_type: str):
        """Отправляет результат генерации пользователю."""
        user_id = message.from_user.id
        
        if not result.get('success'):
            await self._send_generation_error(message)
            return
        
        try:
            if generation_type == 'photo':
                # Отправляем сгенерированное фото
                image_urls = result.get('image_urls', [])
                if image_urls:
                    caption = f"""
✅ **Фото готово!**

🎨 Модель: {result.get('model_used', 'unknown')}
⏱️ Время генерации: {result.get('duration', 0):.1f}с
                    """
                    
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔄 Сгенерировать еще", callback_data="generate_photo")],
                        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
                    ])
                    
                    await message.bot.send_photo(
                        chat_id=user_id,
                        photo=image_urls[0],
                        caption=caption.strip(),
                        reply_markup=keyboard,
                        parse_mode='Markdown'
                    )
                else:
                    await self._send_generation_error(message)
                    
            elif generation_type == 'video':
                # Отправляем сгенерированное видео
                video_url = result.get('video_url')
                if video_url:
                    caption = f"""
✅ **Видео готово!**

⏱️ Длительность: {result.get('duration', 3)}с
                    """
                    
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔄 Сгенерировать еще", callback_data="generate_video")],
                        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
                    ])
                    
                    await message.bot.send_video(
                        chat_id=user_id,
                        video=video_url,
                        caption=caption.strip(),
                        reply_markup=keyboard,
                        parse_mode='Markdown'
                    )
                else:
                    await self._send_generation_error(message)
                    
        except Exception as e:
            logger.error(f"Ошибка отправки результата генерации user_id={user_id}: {e}", exc_info=True)
            await self._send_generation_error(message)
    
    async def _send_generation_error(self, message: Message):
        """Отправляет сообщение об ошибке генерации."""
        error_text = """
❌ **Ошибка генерации**

Произошла техническая ошибка. Ваши ресурсы не были списаны.

Попробуйте еще раз или обратитесь в поддержку.
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="generation_menu")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await self.send_safe_message(message.from_user.id, error_text.strip(), keyboard)


class ImageMessageHandler(BaseMessageHandler):
    """Хендлер для обработки изображений."""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.generation_service = GenerationService()
        self.avatar_photos: dict = {}  # Временное хранение фото для аватаров
    
    @log_handler_call
    @user_required
    async def handle(self, message: Message, state: FSMContext) -> HandlerResult:
        """Обрабатывает загруженное изображение."""
        user_id = message.from_user.id
        
        if not message.photo:
            return HandlerResult.error_result("Сообщение не содержит фото")
        
        try:
            # Получаем данные из состояния
            user_data = await state.get_data()
            generation_type = user_data.get('generation_type')
            
            if generation_type == 'avatar':
                return await self._handle_avatar_photo(message, state)
            else:
                return await self._handle_face_photo(message, state)
                
        except Exception as e:
            logger.error(f"Ошибка обработки изображения для user_id={user_id}: {e}", exc_info=True)
            return HandlerResult.error_result(f"Ошибка обработки изображения: {e}")
    
    async def _handle_avatar_photo(self, message: Message, state: FSMContext) -> HandlerResult:
        """Обрабатывает фото для создания аватара."""
        user_id = message.from_user.id
        
        try:
            # Скачиваем и сохраняем фото
            photo = message.photo[-1]  # Берем фото наибольшего размера
            file_info = await message.bot.get_file(photo.file_id)
            
            # Создаем путь для сохранения
            avatar_dir = f"temp/avatars/{user_id}"
            os.makedirs(avatar_dir, exist_ok=True)
            
            # Инициализируем список фото для пользователя
            if user_id not in self.avatar_photos:
                self.avatar_photos[user_id] = []
            
            photo_count = len(self.avatar_photos[user_id])
            file_path = f"{avatar_dir}/photo_{photo_count + 1}.jpg"
            
            # Скачиваем файл
            await message.bot.download_file(file_info.file_path, file_path)
            self.avatar_photos[user_id].append(file_path)
            
            photo_count = len(self.avatar_photos[user_id])
            
            if photo_count < 3:
                # Нужно еще фото
                await self._request_more_photos(message, photo_count)
                return HandlerResult.success_result(f"Получено фото {photo_count}/3-10")
            elif photo_count < 10:
                # Можно добавить еще или начать обучение
                await self._offer_more_photos_or_start(message, photo_count)
                return HandlerResult.success_result(f"Получено фото {photo_count}/10")
            else:
                # Максимум фото, начинаем обучение
                await self._start_avatar_training(message, state)
                return HandlerResult.success_result("Начато обучение аватара")
                
        except Exception as e:
            logger.error(f"Ошибка обработки фото аватара для user_id={user_id}: {e}", exc_info=True)
            await self._send_avatar_photo_error(message)
            return HandlerResult.error_result(f"Ошибка обработки фото: {e}")
    
    async def _handle_face_photo(self, message: Message, state: FSMContext) -> HandlerResult:
        """Обрабатывает фото лица для генерации."""
        user_id = message.from_user.id
        
        try:
            # Скачиваем фото
            photo = message.photo[-1]
            file_info = await message.bot.get_file(photo.file_id)
            
            # Создаем временный путь
            temp_dir = f"temp/faces/{user_id}"
            os.makedirs(temp_dir, exist_ok=True)
            file_path = f"{temp_dir}/face.jpg"
            
            await message.bot.download_file(file_info.file_path, file_path)
            
            # Сохраняем путь к файлу в состоянии
            await state.update_data(face_image_path=file_path)
            
            # Запрашиваем промпт
            await self._request_prompt_with_face(message)
            await state.set_state(BotStates.AWAITING_PROMPT)
            
            return HandlerResult.success_result("Фото лица получено, запрашиваем промпт")
            
        except Exception as e:
            logger.error(f"Ошибка обработки фото лица для user_id={user_id}: {e}", exc_info=True)
            return HandlerResult.error_result(f"Ошибка обработки фото: {e}")
    
    async def _request_more_photos(self, message: Message, current_count: int):
        """Запрашивает дополнительные фото для аватара."""
        text = f"""
📸 **Фото {current_count}/10 получено**

Отправьте еще фото (минимум 3, рекомендуется 5-10):

✅ Хорошо: разные ракурсы, выражения лица, освещение
❌ Плохо: размытые, темные, с другими людьми
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="generation_menu")]
        ])
        
        await self.send_safe_message(message.from_user.id, text.strip(), keyboard)
    
    async def _offer_more_photos_or_start(self, message: Message, current_count: int):
        """Предлагает добавить еще фото или начать обучение."""
        text = f"""
📸 **Фото {current_count}/10 получено**

У вас достаточно фото для создания аватара. Можете:

• Отправить еще фото (до 10 максимум)
• Начать обучение аватара сейчас
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Начать обучение", callback_data="start_avatar_training")],
            [InlineKeyboardButton(text="📸 Добавить еще фото", callback_data="add_more_photos")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="generation_menu")]
        ])
        
        await self.send_safe_message(message.from_user.id, text.strip(), keyboard)
    
    async def _start_avatar_training(self, message: Message, state: FSMContext):
        """Начинает обучение аватара."""
        user_id = message.from_user.id
        
        try:
            # Создаем запрос на создание аватара
            generation_request = GenerationRequest(
                user_id=user_id,
                generation_type='avatar',
                additional_params={
                    'avatar_name': f'Аватар {user_id}',
                    'photo_paths': self.avatar_photos.get(user_id, [])
                }
            )
            
            # Запускаем создание аватара
            result = await self.generation_service.create_avatar(generation_request)
            
            if result.get('success'):
                success_text = f"""
✅ **Обучение аватара началось!**

🎯 ID аватара: {result.get('avatar_id')}
⏱️ Примерное время: {result.get('estimated_time', 300) // 60} минут

Мы уведомим вас, когда аватар будет готов!
                """
                
                keyboard = await create_main_menu_keyboard(user_id)
                await self.send_safe_message(user_id, success_text.strip(), keyboard)
                
                # Очищаем временные данные
                if user_id in self.avatar_photos:
                    del self.avatar_photos[user_id]
                await state.clear()
            else:
                await self._send_avatar_training_error(message)
                
        except Exception as e:
            logger.error(f"Ошибка запуска обучения аватара для user_id={user_id}: {e}", exc_info=True)
            await self._send_avatar_training_error(message)
    
    async def _request_prompt_with_face(self, message: Message):
        """Запрашивает промпт для генерации с лицом."""
        text = """
✅ **Фото получено!**

Теперь опишите, какое изображение вы хотите создать с вашим лицом:

Примеры:
• "В костюме супергероя на фоне города"
• "В средневековом замке в роли рыцаря"
• "На пляже в летней одежде"
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="generation_menu")]
        ])
        
        await self.send_safe_message(message.from_user.id, text.strip(), keyboard)
    
    async def _send_avatar_photo_error(self, message: Message):
        """Отправляет сообщение об ошибке обработки фото аватара."""
        error_text = """
❌ **Ошибка обработки фото**

Не удалось обработать загруженное фото. Попробуйте:

• Загрузить фото лучшего качества
• Убедиться, что на фото только вы
• Проверить, что фото не слишком большое
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="create_avatar")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await self.send_safe_message(message.from_user.id, error_text.strip(), keyboard)
    
    async def _send_avatar_training_error(self, message: Message):
        """Отправляет сообщение об ошибке обучения аватара."""
        error_text = """
❌ **Ошибка создания аватара**

Не удалось запустить обучение аватара. Ваши ресурсы не были списаны.

Попробуйте еще раз или обратитесь в поддержку.
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="create_avatar")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        
        await self.send_safe_message(message.from_user.id, error_text.strip(), keyboard)