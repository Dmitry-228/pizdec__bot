"""
Сервисы административного домена.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio

import database

logger = logging.getLogger(__name__)


class AdminService:
    """Сервис для административных функций."""
    
    def __init__(self):
        self.db = database()
    
    async def get_admin_stats(self) -> Dict[str, Any]:
        """Получает общую статистику для админов."""
        try:
            # Статистика пользователей
            users_stats = await self._get_users_stats()
            
            # Статистика платежей
            payments_stats = await self._get_payments_stats()
            
            # Статистика генераций
            generations_stats = await self._get_generations_stats()
            
            # Статистика аватаров
            avatars_stats = await self._get_avatars_stats()
            
            # Системная статистика
            system_stats = await self._get_system_stats()
            
            return {
                'users': users_stats,
                'payments': payments_stats,
                'generations': generations_stats,
                'avatars': avatars_stats,
                'system': system_stats,
                'updated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения админ статистики: {e}", exc_info=True)
            return {}
    
    async def _get_users_stats(self) -> Dict[str, Any]:
        """Получает статистику пользователей."""
        query = """
        SELECT 
            COUNT(*) as total_users,
            COUNT(CASE WHEN created_at >= NOW() - INTERVAL '1 day' THEN 1 END) as new_today,
            COUNT(CASE WHEN created_at >= NOW() - INTERVAL '7 days' THEN 1 END) as new_week,
            COUNT(CASE WHEN created_at >= NOW() - INTERVAL '30 days' THEN 1 END) as new_month,
            COUNT(CASE WHEN last_activity >= NOW() - INTERVAL '1 day' THEN 1 END) as active_today,
            COUNT(CASE WHEN last_activity >= NOW() - INTERVAL '7 days' THEN 1 END) as active_week,
            COUNT(CASE WHEN email IS NOT NULL AND email != '' THEN 1 END) as with_email
        FROM users
        """
        
        result = await self.db.fetchrow(query)
        return dict(result) if result else {}
    
    async def _get_payments_stats(self) -> Dict[str, Any]:
        """Получает статистику платежей."""
        query = """
        SELECT 
            COUNT(*) as total_payments,
            COUNT(CASE WHEN created_at >= NOW() - INTERVAL '1 day' THEN 1 END) as payments_today,
            COUNT(CASE WHEN created_at >= NOW() - INTERVAL '7 days' THEN 1 END) as payments_week,
            COUNT(CASE WHEN created_at >= NOW() - INTERVAL '30 days' THEN 1 END) as payments_month,
            COALESCE(SUM(amount), 0) as total_revenue,
            COALESCE(SUM(CASE WHEN created_at >= NOW() - INTERVAL '1 day' THEN amount END), 0) as revenue_today,
            COALESCE(SUM(CASE WHEN created_at >= NOW() - INTERVAL '7 days' THEN amount END), 0) as revenue_week,
            COALESCE(SUM(CASE WHEN created_at >= NOW() - INTERVAL '30 days' THEN amount END), 0) as revenue_month,
            COALESCE(AVG(amount), 0) as avg_payment
        FROM payments 
        WHERE status = 'succeeded'
        """
        
        result = await self.db.fetchrow(query)
        return dict(result) if result else {}
    
    async def _get_generations_stats(self) -> Dict[str, Any]:
        """Получает статистику генераций."""
        query = """
        SELECT 
            COUNT(*) as total_generations,
            COUNT(CASE WHEN created_at >= NOW() - INTERVAL '1 day' THEN 1 END) as generations_today,
            COUNT(CASE WHEN created_at >= NOW() - INTERVAL '7 days' THEN 1 END) as generations_week,
            COUNT(CASE WHEN created_at >= NOW() - INTERVAL '30 days' THEN 1 END) as generations_month,
            COUNT(CASE WHEN status = 'success' THEN 1 END) as successful,
            COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
            COUNT(CASE WHEN status = 'processing' THEN 1 END) as processing
        FROM generations
        """
        
        result = await self.db.fetchrow(query)
        return dict(result) if result else {}
    
    async def _get_avatars_stats(self) -> Dict[str, Any]:
        """Получает статистику аватаров."""
        query = """
        SELECT 
            COUNT(*) as total_avatars,
            COUNT(CASE WHEN created_at >= NOW() - INTERVAL '1 day' THEN 1 END) as avatars_today,
            COUNT(CASE WHEN created_at >= NOW() - INTERVAL '7 days' THEN 1 END) as avatars_week,
            COUNT(CASE WHEN created_at >= NOW() - INTERVAL '30 days' THEN 1 END) as avatars_month,
            COUNT(CASE WHEN status = 'success' THEN 1 END) as successful,
            COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
            COUNT(CASE WHEN status = 'training' THEN 1 END) as training
        FROM avatars
        """
        
        result = await self.db.fetchrow(query)
        return dict(result) if result else {}
    
    async def _get_system_stats(self) -> Dict[str, Any]:
        """Получает системную статистику."""
        # Статистика обратной связи
        feedback_query = """
        SELECT 
            COUNT(*) as total_feedback,
            COUNT(CASE WHEN created_at >= NOW() - INTERVAL '1 day' THEN 1 END) as feedback_today,
            COUNT(CASE WHEN is_resolved = true THEN 1 END) as resolved_feedback
        FROM user_feedback
        """
        
        feedback_result = await self.db.fetchrow(feedback_query)
        
        # Статистика ошибок (если есть таблица)
        try:
            errors_query = """
            SELECT 
                COUNT(*) as total_errors,
                COUNT(CASE WHEN created_at >= NOW() - INTERVAL '1 day' THEN 1 END) as errors_today
            FROM error_logs
            WHERE created_at >= NOW() - INTERVAL '7 days'
            """
            errors_result = await self.db.fetchrow(errors_query)
        except:
            errors_result = {'total_errors': 0, 'errors_today': 0}
        
        return {
            'feedback': dict(feedback_result) if feedback_result else {},
            'errors': dict(errors_result) if errors_result else {}
        }
    
    async def get_user_list(self, page: int = 1, limit: int = 20, search: str = None) -> Dict[str, Any]:
        """Получает список пользователей с пагинацией."""
        try:
            offset = (page - 1) * limit
            
            # Базовый запрос
            where_clause = "WHERE 1=1"
            params = []
            
            # Поиск
            if search:
                where_clause += " AND (first_name ILIKE $1 OR username ILIKE $1 OR email ILIKE $1 OR user_id::text = $1)"
                params.append(f"%{search}%")
            
            # Получаем пользователей
            users_query = f"""
            SELECT 
                user_id, first_name, username, email, created_at, last_activity,
                generations_left, avatar_left, is_admin, is_banned,
                (SELECT COUNT(*) FROM payments WHERE payments.user_id = users.user_id AND status = 'succeeded') as payments_count,
                (SELECT COALESCE(SUM(amount), 0) FROM payments WHERE payments.user_id = users.user_id AND status = 'succeeded') as total_spent
            FROM users 
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
            """
            
            params.extend([limit, offset])
            users = await self.db.fetch(users_query, *params)
            
            # Получаем общее количество
            count_query = f"SELECT COUNT(*) FROM users {where_clause}"
            count_params = params[:-2] if search else []
            total_count = await self.db.fetchval(count_query, *count_params)
            
            return {
                'users': [dict(user) for user in users],
                'total_count': total_count,
                'page': page,
                'limit': limit,
                'total_pages': (total_count + limit - 1) // limit
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения списка пользователей: {e}", exc_info=True)
            return {'users': [], 'total_count': 0, 'page': page, 'limit': limit, 'total_pages': 0}
    
    async def get_user_details(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получает детальную информацию о пользователе."""
        try:
            # Основная информация о пользователе
            user_query = """
            SELECT * FROM users WHERE user_id = $1
            """
            user = await self.db.fetchrow(user_query, user_id)
            
            if not user:
                return None
            
            # Платежи пользователя
            payments_query = """
            SELECT * FROM payments 
            WHERE user_id = $1 
            ORDER BY created_at DESC 
            LIMIT 10
            """
            payments = await self.db.fetch(payments_query, user_id)
            
            # Генерации пользователя
            generations_query = """
            SELECT * FROM generations 
            WHERE user_id = $1 
            ORDER BY created_at DESC 
            LIMIT 10
            """
            generations = await self.db.fetch(generations_query, user_id)
            
            # Аватары пользователя
            avatars_query = """
            SELECT * FROM avatars 
            WHERE user_id = $1 
            ORDER BY created_at DESC
            """
            avatars = await self.db.fetch(avatars_query, user_id)
            
            # Обратная связь от пользователя
            feedback_query = """
            SELECT * FROM user_feedback 
            WHERE user_id = $1 
            ORDER BY created_at DESC 
            LIMIT 5
            """
            feedback = await self.db.fetch(feedback_query, user_id)
            
            return {
                'user': dict(user),
                'payments': [dict(p) for p in payments],
                'generations': [dict(g) for g in generations],
                'avatars': [dict(a) for a in avatars],
                'feedback': [dict(f) for f in feedback]
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения деталей пользователя {user_id}: {e}", exc_info=True)
            return None
    
    async def update_user_resources(self, user_id: int, generations_delta: int = 0, avatars_delta: int = 0) -> bool:
        """Обновляет ресурсы пользователя."""
        try:
            query = """
            UPDATE users 
            SET 
                generations_left = GREATEST(0, generations_left + $2),
                avatar_left = GREATEST(0, avatar_left + $3),
                updated_at = NOW()
            WHERE user_id = $1
            """
            
            result = await self.db.execute(query, user_id, generations_delta, avatars_delta)
            return result == "UPDATE 1"
            
        except Exception as e:
            logger.error(f"Ошибка обновления ресурсов пользователя {user_id}: {e}", exc_info=True)
            return False
    
    async def ban_user(self, user_id: int, reason: str = None) -> bool:
        """Блокирует пользователя."""
        try:
            query = """
            UPDATE users 
            SET 
                is_banned = true,
                ban_reason = $2,
                banned_at = NOW(),
                updated_at = NOW()
            WHERE user_id = $1
            """
            
            result = await self.db.execute(query, user_id, reason)
            return result == "UPDATE 1"
            
        except Exception as e:
            logger.error(f"Ошибка блокировки пользователя {user_id}: {e}", exc_info=True)
            return False
    
    async def unban_user(self, user_id: int) -> bool:
        """Разблокирует пользователя."""
        try:
            query = """
            UPDATE users 
            SET 
                is_banned = false,
                ban_reason = NULL,
                banned_at = NULL,
                updated_at = NOW()
            WHERE user_id = $1
            """
            
            result = await self.db.execute(query, user_id)
            return result == "UPDATE 1"
            
        except Exception as e:
            logger.error(f"Ошибка разблокировки пользователя {user_id}: {e}", exc_info=True)
            return False
    
    async def make_admin(self, user_id: int) -> bool:
        """Делает пользователя администратором."""
        try:
            query = """
            UPDATE users 
            SET 
                is_admin = true,
                updated_at = NOW()
            WHERE user_id = $1
            """
            
            result = await self.db.execute(query, user_id)
            return result == "UPDATE 1"
            
        except Exception as e:
            logger.error(f"Ошибка назначения админа {user_id}: {e}", exc_info=True)
            return False
    
    async def remove_admin(self, user_id: int) -> bool:
        """Убирает права администратора."""
        try:
            query = """
            UPDATE users 
            SET 
                is_admin = false,
                updated_at = NOW()
            WHERE user_id = $1
            """
            
            result = await self.db.execute(query, user_id)
            return result == "UPDATE 1"
            
        except Exception as e:
            logger.error(f"Ошибка удаления прав админа {user_id}: {e}", exc_info=True)
            return False


class FeedbackService:
    """Сервис для управления обратной связью."""
    
    def __init__(self):
        self.db = database()
    
    async def get_feedback_list(self, page: int = 1, limit: int = 10, status: str = None) -> Dict[str, Any]:
        """Получает список обратной связи."""
        try:
            offset = (page - 1) * limit
            
            # Фильтр по статусу
            where_clause = "WHERE 1=1"
            params = []
            
            if status == 'unresolved':
                where_clause += " AND is_resolved = false"
            elif status == 'resolved':
                where_clause += " AND is_resolved = true"
            
            # Получаем обратную связь
            feedback_query = f"""
            SELECT 
                f.*,
                u.first_name, u.username
            FROM user_feedback f
            LEFT JOIN users u ON f.user_id = u.user_id
            {where_clause}
            ORDER BY f.created_at DESC
            LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
            """
            
            params.extend([limit, offset])
            feedback_list = await self.db.fetch(feedback_query, *params)
            
            # Получаем общее количество
            count_query = f"SELECT COUNT(*) FROM user_feedback f {where_clause}"
            count_params = params[:-2]
            total_count = await self.db.fetchval(count_query, *count_params)
            
            return {
                'feedback': [dict(f) for f in feedback_list],
                'total_count': total_count,
                'page': page,
                'limit': limit,
                'total_pages': (total_count + limit - 1) // limit
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения списка обратной связи: {e}", exc_info=True)
            return {'feedback': [], 'total_count': 0, 'page': page, 'limit': limit, 'total_pages': 0}
    
    async def mark_feedback_resolved(self, feedback_id: int, admin_response: str = None) -> bool:
        """Отмечает обратную связь как решенную."""
        try:
            query = """
            UPDATE user_feedback 
            SET 
                is_resolved = true,
                admin_response = $2,
                resolved_at = NOW()
            WHERE feedback_id = $1
            """
            
            result = await self.db.execute(query, feedback_id, admin_response)
            return result == "UPDATE 1"
            
        except Exception as e:
            logger.error(f"Ошибка отметки обратной связи {feedback_id} как решенной: {e}", exc_info=True)
            return False
    
    async def get_feedback_details(self, feedback_id: int) -> Optional[Dict[str, Any]]:
        """Получает детали обратной связи."""
        try:
            query = """
            SELECT 
                f.*,
                u.first_name, u.username, u.email
            FROM user_feedback f
            LEFT JOIN users u ON f.user_id = u.user_id
            WHERE f.feedback_id = $1
            """
            
            result = await self.db.fetchrow(query, feedback_id)
            return dict(result) if result else None
            
        except Exception as e:
            logger.error(f"Ошибка получения деталей обратной связи {feedback_id}: {e}", exc_info=True)
            return None


class SystemService:
    """Сервис для системных функций."""
    
    def __init__(self):
        self.db = database()
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Получает информацию о состоянии системы."""
        try:
            # Проверка подключения к БД
            db_status = await self._check_database_health()
            
            # Статистика очередей (если используются)
            queue_status = await self._check_queue_health()
            
            # Статистика дискового пространства (примерная)
            disk_status = await self._check_disk_health()
            
            return {
                'database': db_status,
                'queues': queue_status,
                'disk': disk_status,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Ошибка проверки состояния системы: {e}", exc_info=True)
            return {'status': 'error', 'error': str(e)}
    
    async def _check_database_health(self) -> Dict[str, Any]:
        """Проверяет состояние базы данных."""
        try:
            # Простой запрос для проверки соединения
            result = await self.db.fetchval("SELECT 1")
            
            # Проверяем размер БД
            size_query = "SELECT pg_size_pretty(pg_database_size(current_database()))"
            db_size = await self.db.fetchval(size_query)
            
            # Количество активных соединений
            connections_query = "SELECT count(*) FROM pg_stat_activity"
            active_connections = await self.db.fetchval(connections_query)
            
            return {
                'status': 'healthy' if result == 1 else 'error',
                'size': db_size,
                'active_connections': active_connections
            }
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    async def _check_queue_health(self) -> Dict[str, Any]:
        """Проверяет состояние очередей."""
        try:
            # Проверяем очереди генераций
            processing_generations = await self.db.fetchval(
                "SELECT COUNT(*) FROM generations WHERE status = 'processing'"
            )
            
            # Проверяем очереди аватаров
            training_avatars = await self.db.fetchval(
                "SELECT COUNT(*) FROM avatars WHERE status = 'training'"
            )
            
            return {
                'status': 'healthy',
                'processing_generations': processing_generations,
                'training_avatars': training_avatars
            }
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    async def _check_disk_health(self) -> Dict[str, Any]:
        """Проверяет состояние дискового пространства."""
        try:
            # Примерная проверка через размер таблиц
            tables_query = """
            SELECT 
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            LIMIT 5
            """
            
            tables = await self.db.fetch(tables_query)
            
            return {
                'status': 'healthy',
                'largest_tables': [dict(t) for t in tables]
            }
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}