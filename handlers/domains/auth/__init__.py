"""
Домен аутентификации и регистрации пользователей.

Отвечает за:
- Регистрацию новых пользователей
- Команду /start
- Обработку реферальных ссылок
- Первичную настройку пользователя
"""

from .handlers import AuthDomainHandler
from .commands import StartCommandHandler
from .callbacks import ReferralCallbackHandler

__all__ = [
    'AuthDomainHandler',
    'StartCommandHandler', 
    'ReferralCallbackHandler'
]