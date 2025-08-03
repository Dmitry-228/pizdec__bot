"""
Исключения для хендлеров.
"""


class HandlerError(Exception):
    """Базовое исключение для хендлеров."""
    
    def __init__(self, message: str, code: str = None):
        self.message = message
        self.code = code
        super().__init__(self.message)


class ValidationError(HandlerError):
    """Ошибка валидации данных."""
    
    def __init__(self, message: str, field: str = None):
        self.field = field
        super().__init__(message, "VALIDATION_ERROR")


class PermissionError(HandlerError):
    """Ошибка прав доступа."""
    
    def __init__(self, message: str = "Недостаточно прав для выполнения операции"):
        super().__init__(message, "PERMISSION_DENIED")


class ResourceError(HandlerError):
    """Ошибка недостатка ресурсов."""
    
    def __init__(self, message: str, resource_type: str = None):
        self.resource_type = resource_type
        super().__init__(message, "RESOURCE_INSUFFICIENT")


class GenerationError(HandlerError):
    """Ошибка генерации контента."""
    
    def __init__(self, message: str, generation_type: str = None):
        self.generation_type = generation_type
        super().__init__(message, "GENERATION_ERROR")


class PaymentError(HandlerError):
    """Ошибка платежа."""
    
    def __init__(self, message: str, payment_id: str = None):
        self.payment_id = payment_id
        super().__init__(message, "PAYMENT_ERROR")


class DatabaseError(HandlerError):
    """Ошибка базы данных."""
    
    def __init__(self, message: str, operation: str = None):
        self.operation = operation
        super().__init__(message, "DATABASE_ERROR")


class ExternalServiceError(HandlerError):
    """Ошибка внешнего сервиса."""
    
    def __init__(self, message: str, service: str = None):
        self.service = service
        super().__init__(message, "EXTERNAL_SERVICE_ERROR")