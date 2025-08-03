"""
Общие компоненты для всех доменов.
"""

from .base import BaseHandler, BaseCallbackHandler, BaseMessageHandler
from .decorators import admin_required, user_required, check_resources
from .exceptions import HandlerError, ValidationError, ResourceError
from .types import HandlerResult, CallbackResult

__all__ = [
    'BaseHandler',
    'BaseCallbackHandler', 
    'BaseMessageHandler',
    'admin_required',
    'user_required',
    'check_resources',
    'HandlerError',
    'ValidationError',
    'ResourceError',
    'HandlerResult',
    'CallbackResult'
]