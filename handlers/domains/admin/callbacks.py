"""
Callback хендлеры административного домена.
"""

import logging
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from keyboards import create_admin_menu_keyboard, create_main_menu_keyboard
from states import BotStates
from ..common.base import BaseCallbackHandler
from ..common.decorators import log_handler_call, admin_required
from ..common.types import CallbackResult
from .services import AdminService, FeedbackService, SystemService

logger = logging.getLogger(__name__)


class AdminMenuCallbackHandler(BaseCallbackHandler):
    """Хендлер для административного меню."""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.admin_service = AdminService()
    
    @log_handler_call
    @admin_required
    async def handle(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Показывает административное меню."""
        try:
            # Получаем краткую статистику
            stats = await self.admin_service.get_admin_stats()
            
            text = await self._format_admin_menu_text(stats)
            keyboard = create_admin_menu_keyboard()
            
            await self.edit_safe_message(query.message, text, keyboard)
            
            return CallbackResult.success_result(
                message="Админ меню показано",
                answer_text="🔧 Панель администратора"
            )
            
        except Exception as e:
            logger.error(f"Ошибка показа админ меню: {e}", exc_info=True)
            return CallbackResult.error_result("Ошибка загрузки админ панели")
    
    async def _format_admin_menu_text(self, stats: dict) -> str:
        """Форматирует текст админ меню."""
        users_stats = stats.get('users', {})
        payments_stats = stats.get('payments', {})
        generations_stats = stats.get('generations', {})
        
        text_parts = [
            "🔧 **Панель администратора**",
            "",
            "📊 **Краткая статистика:**",
            f"👥 Пользователей: {users_stats.get('total_users', 0)}",
            f"📈 Новых сегодня: {users_stats.get('new_today', 0)}",
            f"💰 Платежей сегодня: {payments_stats.get('payments_today', 0)}",
            f"🎨 Генераций сегодня: {generations_stats.get('generations_today', 0)}",
            "",
            "Выберите действие:"
        ]
        
        return "\n".join(text_parts)


class StatsCallbackHandler(BaseCallbackHandler):
    """Хендлер для статистики."""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.admin_service = AdminService()
    
    @log_handler_call
    @admin_required
    async def handle(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Показывает детальную статистику."""
        try:
            stats = await self.admin_service.get_admin_stats()
            
            text = await self._format_detailed_stats(stats)
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_stats")],
                [InlineKeyboardButton(text="🔙 Админ меню", callback_data="admin_menu")]
            ])
            
            await self.edit_safe_message(query.message, text, keyboard)
            
            return CallbackResult.success_result("Статистика показана")
            
        except Exception as e:
            logger.error(f"Ошибка показа статистики: {e}", exc_info=True)
            return CallbackResult.error_result("Ошибка загрузки статистики")
    
    async def _format_detailed_stats(self, stats: dict) -> str:
        """Форматирует детальную статистику."""
        users = stats.get('users', {})
        payments = stats.get('payments', {})
        generations = stats.get('generations', {})
        avatars = stats.get('avatars', {})
        system = stats.get('system', {})
        
        text_parts = [
            "📊 **Детальная статистика**",
            "",
            "👥 **Пользователи:**",
            f"• Всего: {users.get('total_users', 0)}",
            f"• Новых сегодня: {users.get('new_today', 0)}",
            f"• Новых за неделю: {users.get('new_week', 0)}",
            f"• Новых за месяц: {users.get('new_month', 0)}",
            f"• Активных сегодня: {users.get('active_today', 0)}",
            f"• Активных за неделю: {users.get('active_week', 0)}",
            f"• С email: {users.get('with_email', 0)}",
            "",
            "💰 **Платежи:**",
            f"• Всего: {payments.get('total_payments', 0)}",
            f"• Сегодня: {payments.get('payments_today', 0)}",
            f"• За неделю: {payments.get('payments_week', 0)}",
            f"• За месяц: {payments.get('payments_month', 0)}",
            f"• Выручка всего: {payments.get('total_revenue', 0):.2f} RUB",
            f"• Выручка сегодня: {payments.get('revenue_today', 0):.2f} RUB",
            f"• Средний чек: {payments.get('avg_payment', 0):.2f} RUB",
            "",
            "🎨 **Генерации:**",
            f"• Всего: {generations.get('total_generations', 0)}",
            f"• Сегодня: {generations.get('generations_today', 0)}",
            f"• Успешных: {generations.get('successful', 0)}",
            f"• Неудачных: {generations.get('failed', 0)}",
            f"• В обработке: {generations.get('processing', 0)}",
            "",
            "🎭 **Аватары:**",
            f"• Всего: {avatars.get('total_avatars', 0)}",
            f"• Сегодня: {avatars.get('avatars_today', 0)}",
            f"• Успешных: {avatars.get('successful', 0)}",
            f"• Неудачных: {avatars.get('failed', 0)}",
            f"• В обучении: {avatars.get('training', 0)}"
        ]
        
        # Системная статистика
        feedback_stats = system.get('feedback', {})
        if feedback_stats:
            text_parts.extend([
                "",
                "📝 **Обратная связь:**",
                f"• Всего: {feedback_stats.get('total_feedback', 0)}",
                f"• Сегодня: {feedback_stats.get('feedback_today', 0)}",
                f"• Решено: {feedback_stats.get('resolved_feedback', 0)}"
            ])
        
        return "\n".join(text_parts)


class UsersManagementCallbackHandler(BaseCallbackHandler):
    """Хендлер для управления пользователями."""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.admin_service = AdminService()
    
    @log_handler_call
    @admin_required
    async def handle(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Обрабатывает callback'и управления пользователями."""
        callback_data = query.data
        
        if callback_data == "users_list":
            return await self._show_users_list(query, state)
        elif callback_data == "search_user":
            return await self._request_user_search(query, state)
        elif callback_data.startswith("user_details_"):
            user_id = int(callback_data.replace("user_details_", ""))
            return await self._show_user_details(query, user_id)
        elif callback_data.startswith("ban_user_"):
            user_id = int(callback_data.replace("ban_user_", ""))
            return await self._confirm_ban_user(query, user_id)
        elif callback_data.startswith("unban_user_"):
            user_id = int(callback_data.replace("unban_user_", ""))
            return await self._unban_user(query, user_id)
        elif callback_data.startswith("make_admin_"):
            user_id = int(callback_data.replace("make_admin_", ""))
            return await self._make_admin(query, user_id)
        elif callback_data.startswith("remove_admin_"):
            user_id = int(callback_data.replace("remove_admin_", ""))
            return await self._remove_admin(query, user_id)
        elif callback_data.startswith("add_resources_"):
            user_id = int(callback_data.replace("add_resources_", ""))
            return await self._request_add_resources(query, state, user_id)
        else:
            return CallbackResult.error_result("Неизвестная команда управления пользователями")
    
    async def _show_users_list(self, query: CallbackQuery, state: FSMContext, page: int = 1) -> CallbackResult:
        """Показывает список пользователей."""
        try:
            users_data = await self.admin_service.get_user_list(page=page, limit=10)
            
            if not users_data['users']:
                text = "👥 **Пользователи не найдены**"
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Админ меню", callback_data="admin_menu")]
                ])
            else:
                text = await self._format_users_list(users_data)
                keyboard = await self._create_users_list_keyboard(users_data)
            
            await self.edit_safe_message(query.message, text, keyboard)
            
            return CallbackResult.success_result("Список пользователей показан")
            
        except Exception as e:
            logger.error(f"Ошибка показа списка пользователей: {e}", exc_info=True)
            return CallbackResult.error_result("Ошибка загрузки пользователей")
    
    async def _format_users_list(self, users_data: dict) -> str:
        """Форматирует список пользователей."""
        users = users_data['users']
        page = users_data['page']
        total_pages = users_data['total_pages']
        total_count = users_data['total_count']
        
        text_parts = [
            f"👥 **Пользователи** (стр. {page}/{total_pages})",
            f"Всего: {total_count}",
            ""
        ]
        
        for user in users:
            name = user.get('first_name', 'Пользователь')
            username = f"@{user['username']}" if user.get('username') else ""
            
            status_parts = []
            if user.get('is_admin'):
                status_parts.append("👑")
            if user.get('is_banned'):
                status_parts.append("🚫")
            
            status = " ".join(status_parts)
            
            text_parts.append(
                f"**{name}** {username} {status}\n"
                f"ID: {user['user_id']} | 🍪{user.get('generations_left', 0)} 🎭{user.get('avatar_left', 0)}\n"
                f"Потрачено: {user.get('total_spent', 0):.0f} RUB"
            )
            text_parts.append("")
        
        return "\n".join(text_parts)
    
    async def _create_users_list_keyboard(self, users_data: dict) -> InlineKeyboardMarkup:
        """Создает клавиатуру для списка пользователей."""
        users = users_data['users']
        page = users_data['page']
        total_pages = users_data['total_pages']
        
        keyboard_buttons = []
        
        # Кнопки пользователей (по 2 в ряд)
        for i in range(0, len(users), 2):
            row = []
            for j in range(2):
                if i + j < len(users):
                    user = users[i + j]
                    name = user.get('first_name', 'User')[:10]
                    row.append(
                        InlineKeyboardButton(
                            text=f"👤 {name}",
                            callback_data=f"user_details_{user['user_id']}"
                        )
                    )
            keyboard_buttons.append(row)
        
        # Навигация
        nav_row = []
        if page > 1:
            nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"users_page_{page-1}"))
        if page < total_pages:
            nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"users_page_{page+1}"))
        
        if nav_row:
            keyboard_buttons.append(nav_row)
        
        # Дополнительные кнопки
        keyboard_buttons.extend([
            [InlineKeyboardButton(text="🔍 Поиск пользователя", callback_data="search_user")],
            [InlineKeyboardButton(text="🔙 Админ меню", callback_data="admin_menu")]
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    async def _request_user_search(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Запрашивает поиск пользователя."""
        text = """
🔍 **Поиск пользователя**

Введите для поиска:
• Имя пользователя
• Username (без @)
• Email
• ID пользователя

Введите запрос:
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="users_list")]
        ])
        
        await self.edit_safe_message(query.message, text.strip(), keyboard)
        await state.set_state(BotStates.AWAITING_USER_SEARCH)
        
        return CallbackResult.success_result("Запрос поиска пользователя")
    
    async def _show_user_details(self, query: CallbackQuery, user_id: int) -> CallbackResult:
        """Показывает детали пользователя."""
        try:
            user_details = await self.admin_service.get_user_details(user_id)
            
            if not user_details:
                return CallbackResult.error_result("Пользователь не найден")
            
            text = await self._format_user_details(user_details)
            keyboard = await self._create_user_details_keyboard(user_id, user_details['user'])
            
            await self.edit_safe_message(query.message, text, keyboard)
            
            return CallbackResult.success_result("Детали пользователя показаны")
            
        except Exception as e:
            logger.error(f"Ошибка показа деталей пользователя {user_id}: {e}", exc_info=True)
            return CallbackResult.error_result("Ошибка загрузки деталей")
    
    async def _format_user_details(self, user_details: dict) -> str:
        """Форматирует детали пользователя."""
        user = user_details['user']
        payments = user_details['payments']
        generations = user_details['generations']
        avatars = user_details['avatars']
        
        name = user.get('first_name', 'Пользователь')
        username = f"@{user['username']}" if user.get('username') else "не указан"
        email = user.get('email', 'не указан')
        
        text_parts = [
            f"👤 **{name}**",
            f"🆔 ID: {user['user_id']}",
            f"🏷 Username: {username}",
            f"📧 Email: {email}",
            f"📅 Регистрация: {user.get('created_at', '')[:10]}",
            "",
            "💰 **Ресурсы:**",
            f"🍪 Генерации: {user.get('generations_left', 0)}",
            f"🎭 Аватары: {user.get('avatar_left', 0)}",
            "",
            "📊 **Статистика:**",
            f"💳 Платежей: {len(payments)}",
            f"🎨 Генераций: {len(generations)}",
            f"🎭 Аватаров: {len(avatars)}",
        ]
        
        # Статус
        status_parts = []
        if user.get('is_admin'):
            status_parts.append("👑 Администратор")
        if user.get('is_banned'):
            status_parts.append("🚫 Заблокирован")
            if user.get('ban_reason'):
                status_parts.append(f"Причина: {user['ban_reason']}")
        
        if status_parts:
            text_parts.extend(["", "🏷 **Статус:**"] + status_parts)
        
        # Последние платежи
        if payments:
            text_parts.extend(["", "💳 **Последние платежи:**"])
            for payment in payments[:3]:
                amount = payment.get('amount', 0)
                date = payment.get('created_at', '')[:10]
                status = payment.get('status', 'unknown')
                text_parts.append(f"• {amount:.0f} RUB - {date} ({status})")
        
        return "\n".join(text_parts)
    
    async def _create_user_details_keyboard(self, user_id: int, user: dict) -> InlineKeyboardMarkup:
        """Создает клавиатуру для деталей пользователя."""
        keyboard_buttons = []
        
        # Управление ресурсами
        keyboard_buttons.append([
            InlineKeyboardButton(text="➕ Добавить ресурсы", callback_data=f"add_resources_{user_id}")
        ])
        
        # Управление статусом
        if user.get('is_banned'):
            keyboard_buttons.append([
                InlineKeyboardButton(text="✅ Разблокировать", callback_data=f"unban_user_{user_id}")
            ])
        else:
            keyboard_buttons.append([
                InlineKeyboardButton(text="🚫 Заблокировать", callback_data=f"ban_user_{user_id}")
            ])
        
        # Управление правами админа
        if user.get('is_admin'):
            keyboard_buttons.append([
                InlineKeyboardButton(text="👑❌ Убрать админа", callback_data=f"remove_admin_{user_id}")
            ])
        else:
            keyboard_buttons.append([
                InlineKeyboardButton(text="👑✅ Сделать админом", callback_data=f"make_admin_{user_id}")
            ])
        
        # Навигация
        keyboard_buttons.append([
            InlineKeyboardButton(text="🔙 Список пользователей", callback_data="users_list")
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    async def _confirm_ban_user(self, query: CallbackQuery, user_id: int) -> CallbackResult:
        """Запрашивает подтверждение блокировки пользователя."""
        text = f"""
🚫 **Подтверждение блокировки**

Вы действительно хотите заблокировать пользователя ID: {user_id}?

⚠️ Заблокированный пользователь не сможет использовать бота.
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, заблокировать", callback_data=f"confirm_ban_{user_id}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data=f"user_details_{user_id}")
            ]
        ])
        
        await self.edit_safe_message(query.message, text.strip(), keyboard)
        
        return CallbackResult.success_result("Запрос подтверждения блокировки")
    
    async def _unban_user(self, query: CallbackQuery, user_id: int) -> CallbackResult:
        """Разблокирует пользователя."""
        try:
            success = await self.admin_service.unban_user(user_id)
            
            if success:
                text = f"✅ Пользователь {user_id} разблокирован"
                answer_text = "✅ Пользователь разблокирован"
            else:
                text = f"❌ Не удалось разблокировать пользователя {user_id}"
                answer_text = "❌ Ошибка разблокировки"
            
            # Возвращаемся к деталям пользователя
            return await self._show_user_details(query, user_id)
            
        except Exception as e:
            logger.error(f"Ошибка разблокировки пользователя {user_id}: {e}", exc_info=True)
            return CallbackResult.error_result("Ошибка разблокировки")
    
    async def _make_admin(self, query: CallbackQuery, user_id: int) -> CallbackResult:
        """Делает пользователя администратором."""
        try:
            success = await self.admin_service.make_admin(user_id)
            
            if success:
                answer_text = "✅ Пользователь назначен администратором"
            else:
                answer_text = "❌ Ошибка назначения администратора"
            
            # Возвращаемся к деталям пользователя
            result = await self._show_user_details(query, user_id)
            result.answer_text = answer_text
            return result
            
        except Exception as e:
            logger.error(f"Ошибка назначения админа {user_id}: {e}", exc_info=True)
            return CallbackResult.error_result("Ошибка назначения администратора")
    
    async def _remove_admin(self, query: CallbackQuery, user_id: int) -> CallbackResult:
        """Убирает права администратора."""
        try:
            success = await self.admin_service.remove_admin(user_id)
            
            if success:
                answer_text = "✅ Права администратора убраны"
            else:
                answer_text = "❌ Ошибка удаления прав"
            
            # Возвращаемся к деталям пользователя
            result = await self._show_user_details(query, user_id)
            result.answer_text = answer_text
            return result
            
        except Exception as e:
            logger.error(f"Ошибка удаления прав админа {user_id}: {e}", exc_info=True)
            return CallbackResult.error_result("Ошибка удаления прав администратора")
    
    async def _request_add_resources(self, query: CallbackQuery, state: FSMContext, user_id: int) -> CallbackResult:
        """Запрашивает добавление ресурсов пользователю."""
        text = f"""
➕ **Добавление ресурсов**

Пользователь ID: {user_id}

Введите количество ресурсов в формате:
`генерации аватары`

Примеры:
• `10 1` - добавить 10 генераций и 1 аватар
• `5 0` - добавить только 5 генераций
• `0 2` - добавить только 2 аватара
• `-5 0` - убрать 5 генераций

Введите количество:
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"user_details_{user_id}")]
        ])
        
        await self.edit_safe_message(query.message, text.strip(), keyboard)
        await state.set_state(BotStates.AWAITING_RESOURCES_INPUT)
        await state.update_data(target_user_id=user_id)
        
        return CallbackResult.success_result("Запрос добавления ресурсов")


class FeedbackManagementCallbackHandler(BaseCallbackHandler):
    """Хендлер для управления обратной связью."""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.feedback_service = FeedbackService()
    
    @log_handler_call
    @admin_required
    async def handle(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Обрабатывает callback'и управления обратной связью."""
        callback_data = query.data
        
        if callback_data == "feedback_list":
            return await self._show_feedback_list(query, state)
        elif callback_data == "feedback_unresolved":
            return await self._show_feedback_list(query, state, status='unresolved')
        elif callback_data.startswith("feedback_details_"):
            feedback_id = int(callback_data.replace("feedback_details_", ""))
            return await self._show_feedback_details(query, feedback_id)
        elif callback_data.startswith("resolve_feedback_"):
            feedback_id = int(callback_data.replace("resolve_feedback_", ""))
            return await self._resolve_feedback(query, feedback_id)
        else:
            return CallbackResult.error_result("Неизвестная команда управления обратной связью")
    
    async def _show_feedback_list(self, query: CallbackQuery, state: FSMContext, status: str = None, page: int = 1) -> CallbackResult:
        """Показывает список обратной связи."""
        try:
            feedback_data = await self.feedback_service.get_feedback_list(page=page, limit=5, status=status)
            
            if not feedback_data['feedback']:
                status_text = "нерешенной " if status == 'unresolved' else ""
                text = f"📝 **{status_text.title()}обратная связь не найдена**"
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Админ меню", callback_data="admin_menu")]
                ])
            else:
                text = await self._format_feedback_list(feedback_data, status)
                keyboard = await self._create_feedback_list_keyboard(feedback_data, status)
            
            await self.edit_safe_message(query.message, text, keyboard)
            
            return CallbackResult.success_result("Список обратной связи показан")
            
        except Exception as e:
            logger.error(f"Ошибка показа списка обратной связи: {e}", exc_info=True)
            return CallbackResult.error_result("Ошибка загрузки обратной связи")
    
    async def _format_feedback_list(self, feedback_data: dict, status: str = None) -> str:
        """Форматирует список обратной связи."""
        feedback_list = feedback_data['feedback']
        page = feedback_data['page']
        total_pages = feedback_data['total_pages']
        total_count = feedback_data['total_count']
        
        status_text = "нерешенной " if status == 'unresolved' else ""
        
        text_parts = [
            f"📝 **{status_text.title()}Обратная связь** (стр. {page}/{total_pages})",
            f"Всего: {total_count}",
            ""
        ]
        
        for feedback in feedback_list:
            user_name = feedback.get('first_name', 'Пользователь')
            date = feedback.get('created_at', '')[:10]
            text_preview = feedback.get('feedback_text', '')[:50]
            
            if len(feedback.get('feedback_text', '')) > 50:
                text_preview += "..."
            
            resolved_mark = "✅" if feedback.get('is_resolved') else "❌"
            
            text_parts.append(
                f"{resolved_mark} **От: {user_name}** ({date})\n"
                f"ID: {feedback['feedback_id']} | User: {feedback['user_id']}\n"
                f"_{text_preview}_"
            )
            text_parts.append("")
        
        return "\n".join(text_parts)
    
    async def _create_feedback_list_keyboard(self, feedback_data: dict, status: str = None) -> InlineKeyboardMarkup:
        """Создает клавиатуру для списка обратной связи."""
        feedback_list = feedback_data['feedback']
        page = feedback_data['page']
        total_pages = feedback_data['total_pages']
        
        keyboard_buttons = []
        
        # Кнопки обратной связи
        for feedback in feedback_list:
            feedback_id = feedback['feedback_id']
            user_name = feedback.get('first_name', 'User')[:10]
            resolved_mark = "✅" if feedback.get('is_resolved') else "❌"
            
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"{resolved_mark} {user_name}",
                    callback_data=f"feedback_details_{feedback_id}"
                )
            ])
        
        # Навигация
        nav_row = []
        if page > 1:
            callback_prefix = f"feedback_{status}_page_" if status else "feedback_page_"
            nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"{callback_prefix}{page-1}"))
        if page < total_pages:
            callback_prefix = f"feedback_{status}_page_" if status else "feedback_page_"
            nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"{callback_prefix}{page+1}"))
        
        if nav_row:
            keyboard_buttons.append(nav_row)
        
        # Фильтры
        filter_row = []
        if status != 'unresolved':
            filter_row.append(InlineKeyboardButton(text="❌ Нерешенные", callback_data="feedback_unresolved"))
        if status != 'resolved':
            filter_row.append(InlineKeyboardButton(text="✅ Решенные", callback_data="feedback_resolved"))
        if status is not None:
            filter_row.append(InlineKeyboardButton(text="📝 Все", callback_data="feedback_list"))
        
        if filter_row:
            keyboard_buttons.append(filter_row)
        
        # Назад
        keyboard_buttons.append([
            InlineKeyboardButton(text="🔙 Админ меню", callback_data="admin_menu")
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    async def _show_feedback_details(self, query: CallbackQuery, feedback_id: int) -> CallbackResult:
        """Показывает детали обратной связи."""
        try:
            feedback = await self.feedback_service.get_feedback_details(feedback_id)
            
            if not feedback:
                return CallbackResult.error_result("Обратная связь не найдена")
            
            text = await self._format_feedback_details(feedback)
            keyboard = await self._create_feedback_details_keyboard(feedback_id, feedback)
            
            await self.edit_safe_message(query.message, text, keyboard)
            
            return CallbackResult.success_result("Детали обратной связи показаны")
            
        except Exception as e:
            logger.error(f"Ошибка показа деталей обратной связи {feedback_id}: {e}", exc_info=True)
            return CallbackResult.error_result("Ошибка загрузки деталей")
    
    async def _format_feedback_details(self, feedback: dict) -> str:
        """Форматирует детали обратной связи."""
        user_name = feedback.get('first_name', 'Пользователь')
        username = f"@{feedback['username']}" if feedback.get('username') else ""
        email = feedback.get('email', 'не указан')
        date = feedback.get('created_at', '')[:16].replace('T', ' ')
        
        text_parts = [
            f"📝 **Обратная связь #{feedback['feedback_id']}**",
            "",
            f"👤 **От:** {user_name} {username}",
            f"🆔 **User ID:** {feedback['user_id']}",
            f"📧 **Email:** {email}",
            f"📅 **Дата:** {date}",
            "",
            f"💬 **Сообщение:**",
            f"{feedback['feedback_text']}",
            ""
        ]
        
        if feedback.get('is_resolved'):
            text_parts.extend([
                "✅ **Статус:** Решено",
                f"📅 **Решено:** {feedback.get('resolved_at', '')[:16].replace('T', ' ')}"
            ])
            
            if feedback.get('admin_response'):
                text_parts.extend([
                    "",
                    f"👨‍💼 **Ответ администратора:**",
                    f"{feedback['admin_response']}"
                ])
        else:
            text_parts.append("❌ **Статус:** Не решено")
        
        return "\n".join(text_parts)
    
    async def _create_feedback_details_keyboard(self, feedback_id: int, feedback: dict) -> InlineKeyboardMarkup:
        """Создает клавиатуру для деталей обратной связи."""
        keyboard_buttons = []
        
        if not feedback.get('is_resolved'):
            keyboard_buttons.append([
                InlineKeyboardButton(text="✅ Отметить решенным", callback_data=f"resolve_feedback_{feedback_id}")
            ])
        
        # Связаться с пользователем
        keyboard_buttons.append([
            InlineKeyboardButton(text="💬 Написать пользователю", callback_data=f"message_user_{feedback['user_id']}")
        ])
        
        # Назад
        keyboard_buttons.append([
            InlineKeyboardButton(text="🔙 Список обратной связи", callback_data="feedback_list")
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    async def _resolve_feedback(self, query: CallbackQuery, feedback_id: int) -> CallbackResult:
        """Отмечает обратную связь как решенную."""
        try:
            success = await self.feedback_service.mark_feedback_resolved(feedback_id)
            
            if success:
                answer_text = "✅ Обратная связь отмечена как решенная"
            else:
                answer_text = "❌ Ошибка отметки как решенной"
            
            # Возвращаемся к деталям
            result = await self._show_feedback_details(query, feedback_id)
            result.answer_text = answer_text
            return result
            
        except Exception as e:
            logger.error(f"Ошибка отметки обратной связи {feedback_id} как решенной: {e}", exc_info=True)
            return CallbackResult.error_result("Ошибка отметки как решенной")


class SystemCallbackHandler(BaseCallbackHandler):
    """Хендлер для системных функций."""
    
    def __init__(self, bot):
        super().__init__(bot)
        self.system_service = SystemService()
    
    @log_handler_call
    @admin_required
    async def handle(self, query: CallbackQuery, state: FSMContext) -> CallbackResult:
        """Обрабатывает системные callback'и."""
        callback_data = query.data
        
        if callback_data == "system_health":
            return await self._show_system_health(query)
        else:
            return CallbackResult.error_result("Неизвестная системная команда")
    
    async def _show_system_health(self, query: CallbackQuery) -> CallbackResult:
        """Показывает состояние системы."""
        try:
            health = await self.system_service.get_system_health()
            
            text = await self._format_system_health(health)
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Обновить", callback_data="system_health")],
                [InlineKeyboardButton(text="🔙 Админ меню", callback_data="admin_menu")]
            ])
            
            await self.edit_safe_message(query.message, text, keyboard)
            
            return CallbackResult.success_result("Состояние системы показано")
            
        except Exception as e:
            logger.error(f"Ошибка показа состояния системы: {e}", exc_info=True)
            return CallbackResult.error_result("Ошибка загрузки состояния системы")
    
    async def _format_system_health(self, health: dict) -> str:
        """Форматирует информацию о состоянии системы."""
        text_parts = [
            "🔧 **Состояние системы**",
            ""
        ]
        
        # База данных
        db_health = health.get('database', {})
        db_status = "✅" if db_health.get('status') == 'healthy' else "❌"
        text_parts.extend([
            f"{db_status} **База данных:**",
            f"• Размер: {db_health.get('size', 'неизвестно')}",
            f"• Соединений: {db_health.get('active_connections', 0)}",
            ""
        ])
        
        # Очереди
        queue_health = health.get('queues', {})
        queue_status = "✅" if queue_health.get('status') == 'healthy' else "❌"
        text_parts.extend([
            f"{queue_status} **Очереди:**",
            f"• Генераций в обработке: {queue_health.get('processing_generations', 0)}",
            f"• Аватаров в обучении: {queue_health.get('training_avatars', 0)}",
            ""
        ])
        
        # Диск
        disk_health = health.get('disk', {})
        disk_status = "✅" if disk_health.get('status') == 'healthy' else "❌"
        text_parts.extend([
            f"{disk_status} **Хранилище:**"
        ])
        
        largest_tables = disk_health.get('largest_tables', [])
        if largest_tables:
            text_parts.append("• Крупнейшие таблицы:")
            for table in largest_tables[:3]:
                text_parts.append(f"  - {table['tablename']}: {table['size']}")
        
        text_parts.extend([
            "",
            f"🕐 Обновлено: {health.get('timestamp', '')[:16].replace('T', ' ')}"
        ])
        
        return "\n".join(text_parts)
