"""
Команды домена аутентификации.
"""

import logging
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from database import register_user, check_database_user
from keyboards import create_main_menu_keyboard
from ..common.base import BaseMessageHandler
from ..common.decorators import log_handler_call
from ..common.types import HandlerResult

logger = logging.getLogger(__name__)


class StartCommandHandler(BaseMessageHandler):
    """Хендлер команды /start."""
    
    @log_handler_call
    async def handle(self, message: Message, state: FSMContext) -> HandlerResult:
        """Обрабатывает команду /start."""
        user_id = message.from_user.id
        username = message.from_user.username
        first_name = message.from_user.first_name
        
        # Очищаем состояние
        await state.clear()
        
        # Извлекаем реферальный код из команды
        referrer_id = None
        if message.text and len(message.text.split()) > 1:
            try:
                referrer_id = int(message.text.split()[1])
                logger.info(f"Пользователь {user_id} пришел по реферальной ссылке от {referrer_id}")
            except ValueError:
                logger.warning(f"Некорректный реферальный код в команде /start: {message.text}")
        
        # Проверяем, существует ли пользователь
        existing_user = await check_database_user(user_id)
        
        if existing_user:
            # Пользователь уже зарегистрирован
            welcome_text = f"👋 С возвращением, {first_name or username or 'друг'}!\n\n"
            welcome_text += "Выберите действие в меню ниже:"
            
            reply_markup = await create_main_menu_keyboard(user_id)
            await self.send_safe_message(user_id, welcome_text, reply_markup)
            
            return HandlerResult.success_result(
                message="Пользователь вернулся",
                data={"user_id": user_id, "is_new_user": False}
            )
        
        else:
            # Регистрируем нового пользователя
            try:
                success = await register_user(
                    user_id=user_id,
                    username=username,
                    first_name=first_name,
                    referrer_id=referrer_id
                )
                
                if success:
                    welcome_text = f"🎉 Добро пожаловать, {first_name or username or 'друг'}!\n\n"
                    welcome_text += "Вы успешно зарегистрированы в PixelPie Bot.\n"
                    welcome_text += "Теперь вы можете создавать потрясающие фото и видео!\n\n"
                    
                    if referrer_id:
                        welcome_text += "🎁 Спасибо за переход по реферальной ссылке!\n\n"
                    
                    welcome_text += "Выберите действие в меню ниже:"
                    
                    reply_markup = await create_main_menu_keyboard(user_id)
                    await self.send_safe_message(user_id, welcome_text, reply_markup)
                    
                    logger.info(f"Новый пользователь зарегистрирован: {user_id}")
                    
                    return HandlerResult.success_result(
                        message="Пользователь зарегистрирован",
                        data={
                            "user_id": user_id, 
                            "is_new_user": True,
                            "referrer_id": referrer_id
                        }
                    )
                else:
                    error_text = "❌ Произошла ошибка при регистрации. Попробуйте позже."
                    await self.send_safe_message(user_id, error_text)
                    
                    return HandlerResult.error_result("Ошибка регистрации пользователя")
                    
            except Exception as e:
                logger.error(f"Ошибка регистрации пользователя {user_id}: {e}", exc_info=True)
                error_text = "❌ Произошла ошибка при регистрации. Попробуйте позже."
                await self.send_safe_message(user_id, error_text)
                
                return HandlerResult.error_result(f"Исключение при регистрации: {e}")


class HelpCommandHandler(BaseMessageHandler):
    """Хендлер команды /help."""
    
    @log_handler_call
    async def handle(self, message: Message, state: FSMContext) -> HandlerResult:
        """Обрабатывает команду /help."""
        user_id = message.from_user.id
        
        help_text = """
🤖 **PixelPie Bot - Помощь**

**Основные возможности:**
• 📸 Генерация фото по тексту
• 🎭 Создание аватаров
• 🎬 Генерация видео
• 👤 Управление профилем

**Команды:**
/start - Главное меню
/menu - Показать меню
/help - Эта справка

**Поддержка:**
Если у вас возникли вопросы, обратитесь в поддержку через меню бота.

Приятного использования! 🚀
        """
        
        reply_markup = await create_main_menu_keyboard(user_id)
        await self.send_safe_message(user_id, help_text.strip(), reply_markup)
        
        return HandlerResult.success_result(
            message="Справка отправлена",
            data={"user_id": user_id}
        )
