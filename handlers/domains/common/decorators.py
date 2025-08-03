"""
Декораторы для хендлеров.
"""

import functools
import logging
from typing import Callable, Any, Optional, List
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import ADMIN_IDS
from database import check_database_user
from .exceptions import PermissionError, ResourceError, ValidationError
from .types import UserContext

logger = logging.getLogger(__name__)


def admin_required(func: Callable) -> Callable:
    """Декоратор для проверки прав администратора."""
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Ищем объект с user_id среди аргументов
        user_id = None
        
        for arg in args:
            if hasattr(arg, 'from_user') and hasattr(arg.from_user, 'id'):
                user_id = arg.from_user.id
                break
        
        if user_id is None:
            raise ValidationError("Не удалось определить ID пользователя")
        
        if user_id not in ADMIN_IDS:
            logger.warning(f"Попытка доступа без прав администратора: user_id={user_id}")
            raise PermissionError("Недостаточно прав для выполнения операции")
        
        return await func(*args, **kwargs)
    
    return wrapper


def user_required(func: Callable) -> Callable:
    """Декоратор для проверки существования пользователя в БД."""
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Ищем объект с user_id среди аргументов
        user_id = None
        
        for arg in args:
            if hasattr(arg, 'from_user') and hasattr(arg.from_user, 'id'):
                user_id = arg.from_user.id
                break
        
        if user_id is None:
            raise ValidationError("Не удалось определить ID пользователя")
        
        # Проверяем существование пользователя в БД
        user_data = await check_database_user(user_id)
        if not user_data:
            logger.warning(f"Пользователь не найден в БД: user_id={user_id}")
            raise ValidationError("Пользователь не найден в системе")
        
        return await func(*args, **kwargs)
    
    return wrapper


def check_resources(required_photos: int = 0, required_avatars: int = 0):
    """Декоратор для проверки достаточности ресурсов пользователя."""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Ищем объект с user_id среди аргументов
            user_id = None
            
            for arg in args:
                if hasattr(arg, 'from_user') and hasattr(arg.from_user, 'id'):
                    user_id = arg.from_user.id
                    break
            
            if user_id is None:
                raise ValidationError("Не удалось определить ID пользователя")
            
            # Получаем данные пользователя
            user_data = await check_database_user(user_id)
            if not user_data:
                raise ValidationError("Пользователь не найден в системе")
            
            generations_left = user_data[0] if user_data[0] is not None else 0
            avatar_left = user_data[1] if user_data[1] is not None else 0
            
            # Проверяем достаточность ресурсов
            if required_photos > 0 and generations_left < required_photos:
                raise ResourceError(
                    f"Недостаточно печенек! Нужно: {required_photos}, у вас: {generations_left}",
                    "photos"
                )
            
            if required_avatars > 0 and avatar_left < required_avatars:
                raise ResourceError(
                    f"Недостаточно аватаров! Нужно: {required_avatars}, у вас: {avatar_left}",
                    "avatars"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def with_user_context(func: Callable) -> Callable:
    """Декоратор для добавления контекста пользователя в аргументы функции."""
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Ищем объект с user_id среди аргументов
        user_id = None
        username = None
        first_name = None
        
        for arg in args:
            if hasattr(arg, 'from_user'):
                user_id = arg.from_user.id
                username = getattr(arg.from_user, 'username', None)
                first_name = getattr(arg.from_user, 'first_name', None)
                break
        
        if user_id is None:
            raise ValidationError("Не удалось определить ID пользователя")
        
        # Получаем данные пользователя из БД
        user_data = await check_database_user(user_id)
        if not user_data:
            raise ValidationError("Пользователь не найден в системе")
        
        # Создаем контекст пользователя
        user_context = UserContext(
            user_id=user_id,
            username=username,
            first_name=first_name,
            is_admin=user_id in ADMIN_IDS,
            generations_left=user_data[0] if user_data[0] is not None else 0,
            avatar_left=user_data[1] if user_data[1] is not None else 0,
            active_avatar_id=user_data[6] if len(user_data) > 6 else None,
            email=user_data[7] if len(user_data) > 7 else None
        )
        
        # Добавляем контекст в kwargs
        kwargs['user_context'] = user_context
        
        return await func(*args, **kwargs)
    
    return wrapper


def log_handler_call(func: Callable) -> Callable:
    """Декоратор для логирования вызовов хендлеров."""
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Получаем информацию о пользователе для логирования
        user_info = "unknown"
        callback_data = None
        
        for arg in args:
            if hasattr(arg, 'from_user') and hasattr(arg.from_user, 'id'):
                user_info = f"user_id={arg.from_user.id}"
                if hasattr(arg, 'data'):  # CallbackQuery
                    callback_data = arg.data
                break
        
        handler_name = func.__name__
        logger.info(f"Вызов хендлера {handler_name} для {user_info}" + 
                   (f", callback_data={callback_data}" if callback_data else ""))
        
        try:
            result = await func(*args, **kwargs)
            logger.debug(f"Хендлер {handler_name} выполнен успешно для {user_info}")
            return result
        except Exception as e:
            logger.error(f"Ошибка в хендлере {handler_name} для {user_info}: {e}", exc_info=True)
            raise
    
    return wrapper


def rate_limit(calls_per_minute: int = 10):
    """Декоратор для ограничения частоты вызовов."""
    
    def decorator(func: Callable) -> Callable:
        # Здесь можно реализовать логику rate limiting
        # Для простоты пока просто возвращаем функцию как есть
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # TODO: Реализовать rate limiting
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator