"""
Типы данных для хендлеров.
"""

from dataclasses import dataclass
from typing import Optional, Any, Dict
from enum import Enum


class HandlerStatus(Enum):
    """Статусы выполнения хендлеров."""
    SUCCESS = "success"
    ERROR = "error"
    VALIDATION_ERROR = "validation_error"
    PERMISSION_DENIED = "permission_denied"
    RESOURCE_INSUFFICIENT = "resource_insufficient"


@dataclass
class HandlerResult:
    """Результат выполнения хендлера сообщений."""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    status: HandlerStatus = HandlerStatus.SUCCESS
    
    @classmethod
    def success_result(cls, message: str = None, data: Dict[str, Any] = None) -> 'HandlerResult':
        """Создает успешный результат."""
        return cls(success=True, message=message, data=data, status=HandlerStatus.SUCCESS)
    
    @classmethod
    def error_result(cls, error: str, status: HandlerStatus = HandlerStatus.ERROR) -> 'HandlerResult':
        """Создает результат с ошибкой."""
        return cls(success=False, error=error, status=status)


@dataclass
class CallbackResult:
    """Результат выполнения callback хендлера."""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    status: HandlerStatus = HandlerStatus.SUCCESS
    should_answer: bool = True
    answer_text: Optional[str] = None
    show_alert: bool = False
    
    @classmethod
    def success_result(
        cls, 
        message: str = None, 
        data: Dict[str, Any] = None,
        answer_text: str = None,
        show_alert: bool = False
    ) -> 'CallbackResult':
        """Создает успешный результат."""
        return cls(
            success=True, 
            message=message, 
            data=data, 
            status=HandlerStatus.SUCCESS,
            answer_text=answer_text,
            show_alert=show_alert
        )
    
    @classmethod
    def error_result(
        cls, 
        error: str, 
        status: HandlerStatus = HandlerStatus.ERROR,
        show_alert: bool = True
    ) -> 'CallbackResult':
        """Создает результат с ошибкой."""
        return cls(
            success=False, 
            error=error, 
            status=status,
            answer_text=f"❌ {error}",
            show_alert=show_alert
        )


@dataclass
class UserContext:
    """Контекст пользователя для хендлеров."""
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    is_admin: bool = False
    generations_left: int = 0
    avatar_left: int = 0
    active_avatar_id: Optional[int] = None
    email: Optional[str] = None
    
    @property
    def display_name(self) -> str:
        """Возвращает отображаемое имя пользователя."""
        if self.first_name:
            return self.first_name
        elif self.username:
            return f"@{self.username}"
        else:
            return f"ID {self.user_id}"


@dataclass
class GenerationRequest:
    """Запрос на генерацию контента."""
    user_id: int
    generation_type: str  # 'photo', 'video', 'avatar'
    prompt: Optional[str] = None
    style: Optional[str] = None
    model_key: Optional[str] = None
    aspect_ratio: str = "1:1"
    face_image_path: Optional[str] = None
    additional_params: Optional[Dict[str, Any]] = None


@dataclass
class PaymentRequest:
    """Запрос на создание платежа."""
    user_id: int
    tariff_id: str
    amount: float
    description: str
    email: str
    return_url: Optional[str] = None