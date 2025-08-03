#!/usr/bin/env python3
"""
Демонстрация системы логирования
Показывает как использовать различные типы логгеров
"""

from logger import (
    get_logger, log_user_action, log_error, log_api_call,
    log_payment, log_generation
)
import time

def demo_logging_system():
    """Демонстрация всех возможностей системы логирования"""

    print("🚀 Демонстрация системы логирования")
    print("=" * 50)

    # 1. Основное логирование
    print("\n1. Основное логирование:")
    main_logger = get_logger('main')
    main_logger.info("Бот запущен успешно")
    main_logger.warning("Предупреждение: низкий баланс у пользователя 123")

    # 2. Логирование действий пользователя
    print("\n2. Логирование действий пользователя:")
    log_user_action(123, "started_bot", "main", "info")
    log_user_action(456, "generated_avatar", "generation", "info",
                   model="realistic", style="professional")
    log_user_action(789, "payment_failed", "payments", "error",
                   amount=100, reason="insufficient_funds")

    # 3. Логирование ошибок
    print("\n3. Логирование ошибок:")
    try:
        # Симулируем ошибку
        raise ValueError("Тестовая ошибка для демонстрации")
    except Exception as e:
        log_error(e, "demo_function", user_id=123, logger_type="errors")

    # 4. Логирование API вызовов
    print("\n4. Логирование API вызовов:")
    log_api_call("replicate", "/generate", user_id=123, success=True, response_time=2.5)
    log_api_call("telegram", "/send_message", user_id=456, success=False, response_time=0.1)

    # 5. Логирование платежей
    print("\n5. Логирование платежей:")
    log_payment("pay_123456", 123, 100.50, "success", "card")
    log_payment("pay_789012", 456, 50.00, "failed", "crypto")

    # 6. Логирование генераций
    print("\n6. Логирование генераций:")
    log_generation("avatar", 123, "realistic_v1", True, 3.2)
    log_generation("video", 456, "video_v2", False, 15.7)

    # 7. Специализированные логгеры
    print("\n7. Специализированные логгеры:")

    # База данных
    db_logger = get_logger('database')
    db_logger.info("Подключение к базе данных установлено")
    db_logger.error("Ошибка при обновлении пользователя 123")

    # Кнопки
    kb_logger = get_logger('keyboards')
    kb_logger.info("Создана клавиатура для пользователя 456")
    kb_logger.debug("Кнопка 'Генерировать' нажата пользователем 789")

    # Генерации
    gen_logger = get_logger('generation')
    gen_logger.info("Запущена генерация аватара для пользователя 123")
    gen_logger.warning("Медленная генерация для пользователя 456 (15.2s)")

    # API
    api_logger = get_logger('api')
    api_logger.info("API запрос к Replicate выполнен успешно")
    api_logger.error("API запрос к Telegram API завершился ошибкой")

    # Платежи
    pay_logger = get_logger('payments')
    pay_logger.info("Платеж 100.50 руб. успешно обработан")
    pay_logger.error("Ошибка при обработке платежа: неверные данные карты")

    # Ошибки
    err_logger = get_logger('errors')
    err_logger.error("Критическая ошибка в обработчике сообщений")
    err_logger.warning("Предупреждение: пользователь 123 заблокировал бота")

    print("\n✅ Демонстрация завершена!")
    print("\n📁 Проверьте созданные файлы логов:")
    print("   - bot.log (основной лог)")
    print("   - logs/database.log")
    print("   - logs/keyboards.log")
    print("   - logs/generation.log")
    print("   - logs/api.log")
    print("   - logs/payments.log")
    print("   - logs/errors.log")

if __name__ == "__main__":
    demo_logging_system()
