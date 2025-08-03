# onboarding_config.py
# Конфигурация воронки для новых пользователей

from typing import Dict, Any, List
from datetime import timedelta
from logger import get_logger

# Конфигурация воронки
# День 1 = сегодня, День 2 = завтра и т.д.
ONBOARDING_FUNNEL = {
    1: {
        "time_after_registration": timedelta(hours=1),
        "message_type": "welcome",
        "tariff_key": None,  # Все тарифы
        "price": None,
        "description": "Выбери тариф и начни создавать крутые фото"
    },
    2: {
        "time": "11:15",  # Время по МСК
        "message_type": "reminder_day2",
        "tariff_key": "мини",
        "price": 399,
        "description": "Мини-пакет: 10 фото за 399₽. Мгновенный старт, минимальные вложения."
    },
    3: {
        "time": "11:15",
        "message_type": "reminder_day3",
        "tariff_key": "мини",
        "price": 399,
        "description": "Напоминаем: Мини — 10 фото за 399₽. Используй стили, пробуй оживления — фото не сгорят."
    },
    4: {
        "time": "11:15",
        "message_type": "reminder_day4",
        "tariff_key": "лайт",
        "price": 599,
        "description": "Попробуй Лайт: 20 фото за 599₽. Отличный вариант для старта, если хочешь попробовать образы."
    },
    5: {
        "time": "11:15",
        "message_type": "reminder_day5",
        "tariff_key": "комфорт",
        "price": 1199,
        "description": "Пакет Комфорт — 50 фото за 1199₽. Использовать можно когда угодно, образы сохраняются навсегда."
    }
}

# Тексты сообщений
MESSAGE_TEXTS = {
    "welcome": {
        "text": "Привет! Ты уже в PixelPie 🍪 — а значит, твоя фотосессия начинается прямо сейчас. Просто загрузи фото, выбери первый стиль — и получи крутой образ без аватара и ожидания. ИИ работает по твоему селфи — и выдаёт волшебный результат уже через минуту.",
        "button_text": "Загрузить фото",
        "callback_data": "proceed_to_tariff"
    },
    "reminder_day2": {
        "text": "🍪 Мини-пакет: 10 фото за 399₽. Мгновенный старт, минимальные вложения.",
        "button_text": "Купить Лайт-Мини",
        "callback_data": "pay_399"
    },
    "reminder_day3": {
        "text": "🍪 Напоминаем: Мини — 10 фото за 399₽. Используй стили, пробуй оживления — фото не сгорят.",
        "button_text": "Выбрать Мини",
        "callback_data": "pay_399"
    },
    "reminder_day4": {
        "text": "🍪 Попробуй Лайт: 20 фото за 599₽. Отличный вариант для старта, если хочешь попробовать образы.",
        "button_text": "Выбрать Лайт",
        "callback_data": "pay_599"
    },
    "reminder_day5": {
        "text": "🍪 Пакет Комфорт — 50 фото за 1199₽. Использовать можно когда угодно, образы сохраняются навсегда.",
        "button_text": "Выбрать Комфорт",
        "callback_data": "pay_1199"
    }
}

# Функция для получения конфигурации дня
def get_day_config(day: int) -> Dict[str, Any]:
    """Возвращает конфигурацию для указанного дня воронки"""
    return ONBOARDING_FUNNEL.get(day, {})

# Функция для получения текста сообщения
def get_message_text(message_type: str, first_name: str) -> Dict[str, str]:
    """Возвращает текст сообщения для указанного типа"""
    if message_type not in MESSAGE_TEXTS:
        return {}

    text_data = MESSAGE_TEXTS[message_type].copy()
    text_data["text"] = text_data["text"].format(first_name=first_name)
    return text_data

# Функция для проверки, есть ли у пользователя покупки
async def has_user_purchases(user_id: int, database_path: str) -> bool:
    """Проверяет, есть ли у пользователя успешные покупки"""
    import aiosqlite
    try:
        async with aiosqlite.connect(database_path) as conn:
            conn.row_factory = aiosqlite.Row
            c = await conn.cursor()
            await c.execute("""
                SELECT COUNT(*) as count
                FROM payments
                WHERE user_id = ? AND status = 'succeeded'
            """, (user_id,))
            result = await c.fetchone()
            return result['count'] > 0 if result else False
    except Exception as e:
        logger = get_logger('database')
        logger.error(f"Ошибка проверки покупок для user_id={user_id}: {e}")
        return False
