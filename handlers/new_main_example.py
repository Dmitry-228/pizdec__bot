"""
Пример нового упрощенного main.py с доменной архитектурой.

Этот файл показывает, как будет выглядеть main.py после рефакторинга.
Вместо сотен импортов и сложной логики - простая и понятная структура.
"""

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

# Единственный импорт для всех хендлеров
from handlers.domains.registry import DomainRegistry

# Конфигурация
from config import BOT_TOKEN, ADMIN_IDS

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Основная функция запуска бота."""
    
    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Инициализация доменного реестра
    domain_registry = DomainRegistry(bot)
    
    # Регистрация роутера с обработчиками всех доменов
    router = domain_registry.create_router()
    dp.include_router(router)
    
    # Настройка middleware (если нужно)
    # dp.middleware.setup(SomeMiddleware())
    
    # Настройка webhook или polling
    try:
        logger.info("Запуск бота...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}", exc_info=True)
    finally:
        await bot.session.close()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)