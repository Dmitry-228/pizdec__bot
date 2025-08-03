"""
Сервисы для работы с пользователями.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from database import (
    check_database_user, get_user_trainedmodels, get_active_trainedmodel,
    set_active_trainedmodel, delete_trainedmodel, update_user_email
)
from ..common.exceptions import ValidationError, DatabaseError
from ..common.types import UserContext

logger = logging.getLogger(__name__)


class UserService:
    """Сервис для работы с пользователями."""
    
    async def get_user_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получает профиль пользователя."""
        try:
            user_data = await check_database_user(user_id)
            if not user_data:
                return None
            
            # Форматируем данные профиля
            profile = {
                'user_id': user_id,
                'generations_left': user_data[0] if user_data[0] is not None else 0,
                'avatar_left': user_data[1] if user_data[1] is not None else 0,
                'username': user_data[2] if len(user_data) > 2 else None,
                'first_name': user_data[3] if len(user_data) > 3 else None,
                'registration_date': user_data[4] if len(user_data) > 4 else None,
                'first_purchase': user_data[5] if len(user_data) > 5 else True,
                'active_avatar_id': user_data[6] if len(user_data) > 6 else None,
                'email': user_data[7] if len(user_data) > 7 else None,
                'referrer_id': user_data[8] if len(user_data) > 8 else None,
                'referrals_count': user_data[9] if len(user_data) > 9 else 0,
                'payments_count': user_data[10] if len(user_data) > 10 else 0,
                'total_spent': user_data[11] if len(user_data) > 11 else 0.0
            }
            
            return profile
            
        except Exception as e:
            logger.error(f"Ошибка получения профиля user_id={user_id}: {e}", exc_info=True)
            raise DatabaseError(f"Не удалось получить профиль: {e}")
    
    async def update_user_email(self, user_id: int, email: str) -> bool:
        """Обновляет email пользователя."""
        try:
            # Валидация email
            if not self._is_valid_email(email):
                raise ValidationError("Некорректный email адрес")
            
            success = await update_user_email(user_id, email)
            if success:
                logger.info(f"Email обновлен для user_id={user_id}")
                return True
            else:
                raise DatabaseError("Не удалось обновить email в базе данных")
                
        except Exception as e:
            logger.error(f"Ошибка обновления email для user_id={user_id}: {e}", exc_info=True)
            raise
    
    def _is_valid_email(self, email: str) -> bool:
        """Проверяет корректность email адреса."""
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_pattern, email) is not None
    
    async def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """Получает статистику пользователя."""
        try:
            # Здесь можно добавить запросы к базе для получения статистики
            # Пока возвращаем заглушку
            stats = {
                'total_generations': 0,
                'successful_generations': 0,
                'failed_generations': 0,
                'total_avatars_created': 0,
                'active_avatars': 0,
                'total_spent': 0.0,
                'registration_date': None,
                'last_activity': None
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики для user_id={user_id}: {e}", exc_info=True)
            return {}


class AvatarService:
    """Сервис для работы с аватарами пользователей."""
    
    async def get_user_avatars(self, user_id: int) -> List[Dict[str, Any]]:
        """Получает список аватаров пользователя."""
        try:
            avatars_data = await get_user_trainedmodels(user_id)
            
            avatars = []
            for avatar in avatars_data:
                avatar_info = {
                    'avatar_id': avatar[0],
                    'model_id': avatar[1],
                    'model_version': avatar[2],
                    'status': avatar[3],
                    'prediction_id': avatar[4] if len(avatar) > 4 else None,
                    'avatar_name': avatar[5] if len(avatar) > 5 else f'Аватар {avatar[0]}',
                    'created_at': avatar[6] if len(avatar) > 6 else None,
                    'trigger_word': avatar[7] if len(avatar) > 7 else None
                }
                avatars.append(avatar_info)
            
            return avatars
            
        except Exception as e:
            logger.error(f"Ошибка получения аватаров для user_id={user_id}: {e}", exc_info=True)
            raise DatabaseError(f"Не удалось получить аватары: {e}")
    
    async def get_active_avatar(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получает активный аватар пользователя."""
        try:
            active_avatar = await get_active_trainedmodel(user_id)
            
            if not active_avatar:
                return None
            
            return {
                'avatar_id': active_avatar[0],
                'model_id': active_avatar[1],
                'model_version': active_avatar[2],
                'status': active_avatar[3],
                'prediction_id': active_avatar[4] if len(active_avatar) > 4 else None,
                'avatar_name': active_avatar[5] if len(active_avatar) > 5 else f'Аватар {active_avatar[0]}',
                'created_at': active_avatar[6] if len(active_avatar) > 6 else None,
                'trigger_word': active_avatar[7] if len(active_avatar) > 7 else None
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения активного аватара для user_id={user_id}: {e}", exc_info=True)
            raise DatabaseError(f"Не удалось получить активный аватар: {e}")
    
    async def set_active_avatar(self, user_id: int, avatar_id: int) -> bool:
        """Устанавливает активный аватар пользователя."""
        try:
            # Проверяем, что аватар принадлежит пользователю
            user_avatars = await self.get_user_avatars(user_id)
            avatar_exists = any(avatar['avatar_id'] == avatar_id for avatar in user_avatars)
            
            if not avatar_exists:
                raise ValidationError("Аватар не найден или не принадлежит пользователю")
            
            # Проверяем статус аватара
            target_avatar = next((a for a in user_avatars if a['avatar_id'] == avatar_id), None)
            if target_avatar and target_avatar['status'] != 'success':
                raise ValidationError("Аватар еще не готов или имеет ошибки")
            
            success = await set_active_trainedmodel(user_id, avatar_id)
            if success:
                logger.info(f"Активный аватар установлен: user_id={user_id}, avatar_id={avatar_id}")
                return True
            else:
                raise DatabaseError("Не удалось установить активный аватар")
                
        except Exception as e:
            logger.error(f"Ошибка установки активного аватара для user_id={user_id}: {e}", exc_info=True)
            raise
    
    async def delete_avatar(self, user_id: int, avatar_id: int) -> bool:
        """Удаляет аватар пользователя."""
        try:
            # Проверяем, что аватар принадлежит пользователю
            user_avatars = await self.get_user_avatars(user_id)
            avatar_exists = any(avatar['avatar_id'] == avatar_id for avatar in user_avatars)
            
            if not avatar_exists:
                raise ValidationError("Аватар не найден или не принадлежит пользователю")
            
            success = await delete_trainedmodel(avatar_id)
            if success:
                logger.info(f"Аватар удален: user_id={user_id}, avatar_id={avatar_id}")
                return True
            else:
                raise DatabaseError("Не удалось удалить аватар")
                
        except Exception as e:
            logger.error(f"Ошибка удаления аватара для user_id={user_id}: {e}", exc_info=True)
            raise
    
    async def get_avatar_status(self, avatar_id: int) -> Optional[str]:
        """Получает статус аватара."""
        try:
            # Здесь можно добавить запрос к API для получения актуального статуса
            # Пока возвращаем статус из базы данных
            from database import get_trainedmodel_by_id
            
            avatar_data = await get_trainedmodel_by_id(avatar_id)
            if avatar_data:
                return avatar_data.get('status')
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения статуса аватара {avatar_id}: {e}", exc_info=True)
            return None
    
    def format_avatar_status(self, status: str) -> str:
        """Форматирует статус аватара для отображения."""
        status_map = {
            'pending': '⏳ Ожидает обработки',
            'processing': '🔄 Обрабатывается',
            'training': '🎓 Обучается',
            'success': '✅ Готов',
            'failed': '❌ Ошибка',
            'canceled': '🚫 Отменен'
        }
        
        return status_map.get(status, f'❓ Неизвестно ({status})')
    
    def get_avatar_display_name(self, avatar: Dict[str, Any]) -> str:
        """Получает отображаемое имя аватара."""
        name = avatar.get('avatar_name')
        if name and name != f"Аватар {avatar.get('avatar_id')}":
            return name
        
        # Генерируем имя на основе даты создания
        created_at = avatar.get('created_at')
        if created_at:
            try:
                if isinstance(created_at, str):
                    date_obj = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                else:
                    date_obj = created_at
                return f"Аватар от {date_obj.strftime('%d.%m.%Y')}"
            except:
                pass
        
        return f"Аватар #{avatar.get('avatar_id', 'Unknown')}"


class SettingsService:
    """Сервис для работы с настройками пользователя."""
    
    async def get_user_settings(self, user_id: int) -> Dict[str, Any]:
        """Получает настройки пользователя."""
        try:
            # Здесь можно добавить получение настроек из базы данных
            # Пока возвращаем настройки по умолчанию
            settings = {
                'notifications_enabled': True,
                'email_notifications': True,
                'generation_quality': 'high',
                'default_style': 'realistic',
                'auto_save_generations': True,
                'language': 'ru'
            }
            
            return settings
            
        except Exception as e:
            logger.error(f"Ошибка получения настроек для user_id={user_id}: {e}", exc_info=True)
            return {}
    
    async def update_user_settings(self, user_id: int, settings: Dict[str, Any]) -> bool:
        """Обновляет настройки пользователя."""
        try:
            # Валидация настроек
            valid_settings = self._validate_settings(settings)
            
            # Здесь можно добавить сохранение настроек в базу данных
            # Пока просто логируем
            logger.info(f"Настройки обновлены для user_id={user_id}: {valid_settings}")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обновления настроек для user_id={user_id}: {e}", exc_info=True)
            raise
    
    def _validate_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Валидирует настройки пользователя."""
        valid_settings = {}
        
        # Валидация булевых настроек
        bool_settings = ['notifications_enabled', 'email_notifications', 'auto_save_generations']
        for setting in bool_settings:
            if setting in settings:
                valid_settings[setting] = bool(settings[setting])
        
        # Валидация строковых настроек с ограниченными значениями
        if 'generation_quality' in settings:
            if settings['generation_quality'] in ['low', 'medium', 'high']:
                valid_settings['generation_quality'] = settings['generation_quality']
        
        if 'default_style' in settings:
            valid_styles = ['realistic', 'artistic', 'anime', 'portrait']
            if settings['default_style'] in valid_styles:
                valid_settings['default_style'] = settings['default_style']
        
        if 'language' in settings:
            valid_languages = ['ru', 'en']
            if settings['language'] in valid_languages:
                valid_settings['language'] = settings['language']
        
        return valid_settings