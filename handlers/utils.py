import re
from aiogram import Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter, TelegramNetworkError, TelegramForbiddenError
from aiogram.enums import ParseMode
import logging
import tenacity
from aiogram.fsm.context import FSMContext
import uuid
import copy
from typing import Optional, Union, Dict

from config import TARIFFS, YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY, ADMIN_IDS

from logger import get_logger
logger = get_logger('main')

# Проверка наличия YooKassa
try:
    from yookassa import Configuration as YooKassaConfiguration, Payment as YooKassaPayment
    YOOKASSA_AVAILABLE = True
except ImportError:
    YOOKASSA_AVAILABLE = False
    logger.warning("Библиотека yookassa не установлена. Функции оплаты не будут работать.")

# Декоратор для retry при работе с Telegram API
retry_telegram_call = tenacity.retry(
    retry=tenacity.retry_if_exception_type((TelegramNetworkError, TelegramRetryAfter)),
    wait=tenacity.wait_exponential(multiplier=1, min=1, max=10),
    stop=tenacity.stop_after_attempt(3),
    before_sleep=tenacity.before_sleep_log(logger, logging.WARNING),
    reraise=True
)

def safe_escape_markdown(text: str, exclude_chars: Optional[list] = None, version: int = 2) -> str:
    if not text:
        return ""

    text = str(text)

    if version == 1:
        # Экранирование для Markdown
        special_chars = ['_', '*', '`', '[']
    else:
        # Экранирование для MarkdownV2
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']

    # Экранируем все специальные символы
    for char in special_chars:
        text = text.replace(char, f'\\{char}')

    # Исключаем символы, которые не нужно экранировать
    if exclude_chars:
        for char in exclude_chars:
            text = text.replace(f'\\{char}', char)

    logger.debug(f"Escaped text (version={version}): {text[:200]}...")
    return text

def format_user_info_safe(name: str, username: str = None, user_id: int = None, email: str = None) -> str:
    """
    Безопасно форматирует информацию о пользователе для Markdown.
    """
    safe_name = safe_escape_markdown(str(name))

    text = f"👤 Детальная информация о пользователе\n"
    text += f"Имя: {safe_name}"

    if username:
        safe_username = safe_escape_markdown(str(username))
        text += f" \\(@{safe_username}\\)"

    text += f"\n"

    if user_id:
        safe_user_id = safe_escape_markdown(str(user_id))
        text += f"ID: `{safe_user_id}`\n"

    if email:
        safe_email = safe_escape_markdown(str(email))
        text += f"Email: {safe_email}\n"

    return text

def format_balance_info_safe(photo_balance: int, avatar_balance: int) -> str:
    """
    Безопасно форматирует информацию о балансе для Markdown.
    """
    text = "💰 Баланс:\n"
    text += f"  • Печеньки: `{safe_escape_markdown(str(photo_balance))}`\n"
    text += f"  • Аватары: `{safe_escape_markdown(str(avatar_balance))}`\n"

    return text

def format_stats_info_safe(stats_data: dict) -> str:
    """
    Безопасно форматирует статистику для Markdown.
    """
    text = "📊 Статистика генераций:\n"

    for key, value in stats_data.items():
        safe_key = safe_escape_markdown(str(key))
        safe_value = safe_escape_markdown(str(value))
        text += f"  • {safe_key}: `{safe_value}`\n"

    return text

async def format_user_detail_message(user_data: dict) -> str:
    """
    Форматирует детальную информацию о пользователе для админской панели.
    """
    name = user_data.get('first_name', 'Неизвестно')
    username = user_data.get('username', '')
    user_id = user_data.get('user_id', 0)
    email = user_data.get('email', '')
    photo_balance = user_data.get('photo_balance', 0)
    avatar_balance = user_data.get('avatar_balance', 0)

    stats = {
        'Фото по тексту': user_data.get('text_generations', 0),
        'Фото с лицом': user_data.get('face_generations', 0),
        'Аватары': user_data.get('avatar_generations', 0),
        'Видео': user_data.get('video_generations', 0)
    }

    message_text = format_user_info_safe(name, username, user_id, email)
    message_text += format_balance_info_safe(photo_balance, avatar_balance)
    message_text += format_stats_info_safe(stats)

    return message_text

@retry_telegram_call
async def safe_edit_message(
    message: Message,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = ParseMode.MARKDOWN_V2,
    disable_web_page_preview: bool = True
) -> Optional[Message]:
    """
    Безопасно редактирует сообщение с обработкой ошибок Markdown.
    """
    if not message:
        return None

    try:
        return await message.edit_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview
        )
    except TelegramBadRequest as e:
        error_str = str(e).lower()

        if "message is not modified" in error_str:
            logger.info(f"Сообщение не изменено (API): {e}")
            return message

        elif "can't parse entities" in error_str or "can't parse" in error_str:
            logger.warning(f"Ошибка парсинга Markdown: {e}")
            logger.debug(f"Проблемный текст: {text[:200]}...")

            try:
                return await message.edit_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=None,
                    disable_web_page_preview=disable_web_page_preview
                )
            except Exception as e_plain:
                logger.error(f"Не удалось отредактировать без форматирования: {e_plain}")
                return None

        else:
            logger.error(f"BadRequest при редактировании сообщения: {e}")
            return None

    except Exception as e:
        logger.error(f"Неожиданная ошибка при редактировании сообщения: {e}", exc_info=True)
        return None

@retry_telegram_call
async def send_message_with_fallback(
    bot: Bot,
    chat_id: int,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    parse_mode: Optional[str] = ParseMode.MARKDOWN_V2,
    disable_web_page_preview: bool = True
) -> Optional[Message]:
    """
    Безопасно отправляет сообщение с обработкой ошибок парсинга Markdown.
    """
    logger.debug(f"send_message_with_fallback: chat_id={chat_id}, text={text[:200]}..., parse_mode={parse_mode}")

    # Проверка, не является ли chat_id идентификатором самого бота
    bot_info = await bot.get_me()
    if chat_id == bot_info.id:
        logger.error(f"Попытка отправить сообщение самому боту: chat_id={chat_id} совпадает с bot_id={bot_info.id}")
        return None

    try:
        await bot.send_chat_action(chat_id=chat_id, action="typing")
    except Exception as e:
        logger.debug(f"Не удалось отправить typing action: {e}")

    try:
        sent_message = await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview
        )
        logger.debug(f"Message sent successfully: chat_id={chat_id}, message_id={sent_message.message_id}")
        return sent_message
    except TelegramBadRequest as e:
        error_str = str(e).lower()

        if "can't parse entities" in error_str:
            logger.warning(f"Ошибка парсинга Markdown при отправке: {e}")
            logger.debug(f"Проблемный текст: {text[:200]}...")

            try:
                sent_message = await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=None,
                    disable_web_page_preview=disable_web_page_preview
                )
                logger.debug(f"Message sent without formatting: chat_id={chat_id}, message_id={sent_message.message_id}")
                return sent_message
            except Exception as e_plain:
                logger.error(f"Не удалось отправить сообщение без форматирования: {e_plain}")
                try:
                    error_message = await bot.send_message(
                        chat_id=chat_id,
                        text="❌ Произошла ошибка при отправке сообщения. Пожалуйста, попробуйте позже.",
                        parse_mode=None
                    )
                    logger.debug(f"Fallback error message sent: chat_id={chat_id}, message_id={error_message.message_id}")
                    return error_message
                except Exception as e_fallback:
                    logger.error(f"Критическая ошибка: не удалось отправить даже простое сообщение: {e_fallback}")
                    return None
        else:
            logger.error(f"BadRequest при отправке сообщения: {e}")
            return None
    except TelegramForbiddenError as e:
        logger.error(f"Запрещено отправлять сообщение в chat_id={chat_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения для chat_id={chat_id}: {e}", exc_info=True)
        return None

@retry_telegram_call
async def safe_answer_callback(query: CallbackQuery, text: Optional[str] = None, show_alert: bool = False) -> None:
    """
    Безопасно отвечает на callback query.
    """
    if query:
        try:
            await query.answer(text=text, show_alert=show_alert)
        except Exception as e:
            logger.warning(f"Не удалось ответить на CallbackQuery: {e}")

async def delete_message_safe(message: Message) -> None:
    """
    Безопасно удаляет сообщение.
    """
    if message:
        try:
            await message.delete()
        except Exception as e:
            logger.debug(f"Не удалось удалить сообщение: {e}")

async def send_typing_action(bot: Bot, chat_id: int) -> None:
    """
    Отправляет действие 'печатает'.
    """
    try:
        await bot.send_chat_action(chat_id=chat_id, action="typing")
    except Exception as e:
        logger.debug(f"Не удалось отправить typing action: {e}")

async def send_upload_photo_action(bot: Bot, chat_id: int) -> None:
    """
    Отправляет действие 'загружает фото'.
    """
    try:
        await bot.send_chat_action(chat_id=chat_id, action="upload_photo")
    except Exception as e:
        logger.debug(f"Не удалось отправить upload_photo action: {e}")

async def send_upload_video_action(bot: Bot, chat_id: int) -> None:
    """
    Отправляет действие 'загружает видео'.
    """
    try:
        await bot.send_chat_action(chat_id=chat_id, action="upload_video")
    except Exception as e:
        logger.debug(f"Не удалось отправить upload_video action: {e}")

async def clean_admin_context(context: FSMContext) -> None:

    try:
        if not isinstance(context, FSMContext):
            logger.error(f"Ожидался объект FSMContext, получен {type(context)}")
            return

        data = await context.get_data()
        admin_keys = [
            'admin_generation_for_user',
            'admin_target_user_id',
            'is_admin_generation',
            'generation_type',
            'model_key',
            'active_model_version',
            'active_trigger_word',
            'active_avatar_name',
            'style_key',
            'selected_prompt',
            'user_prompt',
            'face_image_path',
            'photo_to_photo_image_path',
            'awaiting_activity_dates',
            'awaiting_support_message'
        ]
        if data:
            new_data = {k: v for k, v in data.items() if k not in admin_keys}
            await context.set_data(new_data)
            if admin_keys:
                logger.debug(f"Очищены админские ключи: {admin_keys}")
            else:
                logger.debug("Контекст не содержал админских ключей для очистки")
        else:
            logger.debug("Контекст пуст, очистка не требуется")
    except Exception as e:
        logger.error(f"Ошибка очистки админского контекста: {e}", exc_info=True)

def create_isolated_context(original_context: Dict, target_user_id: int) -> Dict:
    """
    Создает изолированный контекст для админских операций.
    """
    return {
        'bot': original_context.get('bot'),
        'user_data': copy.deepcopy(original_context.get('user_data', {}).get(target_user_id, {})),
        'chat_data': {},
    }

async def check_user_permissions(message: Message, required_permissions: Optional[list] = None) -> bool:
    """
    Проверяет права пользователя.
    """
    user_id = message.from_user.id

    if required_permissions is None:
        return True

    if 'admin' in required_permissions and user_id not in ADMIN_IDS:
        await message.answer(
            safe_escape_markdown("❌ У вас нет прав для выполнения этой команды."),
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return False

    return True

def get_user_display_name(user: Dict) -> str:
    """
    Получает отображаемое имя пользователя.
    """
    if user.get('first_name'):
        name = user['first_name']
        if user.get('last_name'):
            name += f" {user['last_name']}"
        return name
    elif user.get('username'):
        return f"@{user['username']}"
    else:
        return f"User {user.get('id', 'Unknown')}"

def format_user_mention(user: Dict, escape: bool = True) -> str:
    """
    Форматирует упоминание пользователя.
    """
    display_name = get_user_display_name(user)

    if user.get('username'):
        mention = f"{display_name} (@{user['username']})"
    else:
        mention = f"{display_name} (ID: {user.get('id', 'Unknown')})"

    return safe_escape_markdown(mention) if escape else mention

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Обрезает текст до указанной длины.
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def get_tariff_text(first_purchase: bool = False, is_paying_user: bool = False, time_since_registration: float = float('inf')) -> str:
    """Формирует текст тарифов с корректным экранированием для MarkdownV2."""
    header1 = safe_escape_markdown("🔥 Горячий выбор для идеальных фото и видео!", version=2)
    header2 = safe_escape_markdown("Хочешь крутые кадры без лишних хлопот? Выбирай выгодный пакет и получай фото или видео в один клик!", version=2)
    gift_text_unconditional = safe_escape_markdown(" При первой покупке ЛЮБОГО пакета (кроме 'Только аватар') - 1 аватар в подарок!", version=2)
    footer = safe_escape_markdown("Выбери свой тариф ниже, нажав на соответствующую кнопку ⤵️", version=2)

    # Создаем ссылку в формате MarkdownV2
    terms_link_text = safe_escape_markdown("пользовательским соглашением", version=2)
    terms_text = f"\n\n📄 Приобретая пакет, вы соглашаетесь с [{terms_link_text}](https://telegra.ph/Polzovatelskoe-soglashenie-07-26-12)"

    text_parts = [header1, header2, "\n"]

    available_tariffs = {k: v for k, v in TARIFFS.items() if k != "admin_premium"}

    # Фильтрация тарифов для неоплативших пользователей
    if not is_paying_user:
        if time_since_registration <= 1800:  # 30 минут
            available_tariffs = {k: v for k, v in available_tariffs.items() if k in ["комфорт"]}
        elif time_since_registration <= 5400:  # 30–90 минут
            available_tariffs = {k: v for k, v in available_tariffs.items() if k in ["комфорт", "лайт"]}
        # После 90 минут "мини" доступен

    for _, details in available_tariffs.items():
        text_parts.append(safe_escape_markdown(details['display'], version=2) + "\n")

    if first_purchase:
        text_parts.append(f"\n{gift_text_unconditional}\n")
    else:
        text_parts.append("\n")

    text_parts.append(footer)
    text_parts.append(terms_text)
    return "".join(text_parts)


async def check_resources(bot: Bot, user_id: int, required_photos: int = 0, required_avatars: int = 0) -> Optional[tuple]:
    """
    Проверяет, достаточно ли ресурсов у пользователя.
    """
    from database import check_database_user
    from keyboards import create_main_menu_keyboard, create_subscription_keyboard

    try:
        subscription_data = await check_database_user(user_id)
        logger.debug(f"[check_resources] Получены данные подписки для user_id={user_id}: {subscription_data}")

        if not subscription_data:
            logger.error(f"Нет данных подписки для user_id={user_id}")
            error_text = safe_escape_markdown("❌ Ошибка получения данных подписки. Попробуйте позже.", version=2)
            main_menu_kb = await create_main_menu_keyboard(user_id)
            await send_message_with_fallback(bot, user_id, error_text, reply_markup=main_menu_kb, parse_mode=ParseMode.MARKDOWN_V2)
            return None

        if len(subscription_data) < 9:
            logger.error(f"Неполные данные подписки для user_id={user_id}: {subscription_data}")
            error_text = safe_escape_markdown("❌ Ошибка сервера. Обратитесь в поддержку.", version=2)
            main_menu_kb = await create_main_menu_keyboard(user_id)
            await send_message_with_fallback(bot, user_id, error_text, reply_markup=main_menu_kb, parse_mode=ParseMode.MARKDOWN_V2)
            return None

        generations_left = subscription_data[0] if subscription_data[0] is not None else 0
        avatar_left = subscription_data[1] if subscription_data[1] is not None else 0

        logger.info(f"Проверка ресурсов для user_id={user_id}: фото={generations_left}, аватары={avatar_left}")
        logger.info(f"Требуется: фото={required_photos}, аватары={required_avatars}")

        error_message_parts = []

        if required_photos > 0 and generations_left < required_photos:
            error_message_parts.append(f"🚫 Недостаточно печенек! Нужно: {required_photos}, у тебя: {generations_left}")

        if required_avatars > 0 and avatar_left < required_avatars:
            error_message_parts.append(f"🚫 Недостаточно аватаров! Нужно: {required_avatars}, у тебя: {avatar_left}")

        if error_message_parts:
            error_summary = "\n".join(error_message_parts)
            first_purchase = subscription_data[5] if len(subscription_data) > 5 else True
            tariff_message_text = get_tariff_text(first_purchase, hide_mini_tariff=True)

            full_message = f"{safe_escape_markdown(error_summary, version=2)}\n\n{tariff_message_text}"
            subscription_kb = await create_subscription_keyboard(hide_mini_tariff=True)
            await send_message_with_fallback(bot, user_id, full_message, reply_markup=subscription_kb, parse_mode=ParseMode.MARKDOWN_V2)
            return None

        logger.debug(f"[check_resources] Ресурсы достаточны для user_id={user_id}, возвращаем: {subscription_data}")
        return subscription_data

    except Exception as e:
        logger.error(f"[check_resources] Ошибка проверки ресурсов user_id={user_id}: {e}", exc_info=True)
        error_text = safe_escape_markdown("❌ Ошибка сервера при проверке баланса! Попробуйте позже.", version=2)
        main_menu_kb = await create_main_menu_keyboard(user_id)
        await send_message_with_fallback(bot, user_id, error_text, reply_markup=main_menu_kb, parse_mode=ParseMode.MARKDOWN_V2)
        return None

async def check_active_avatar(bot: Bot, user_id: int) -> Optional[tuple]:
    """
    Проверяет наличие активного аватара у пользователя.
    """
    from database import get_active_trainedmodel
    from keyboards import create_user_profile_keyboard, create_main_menu_keyboard

    try:
        trained_model = await get_active_trainedmodel(user_id)
        if not trained_model or trained_model[3] != 'success':
            logger.warning(f"[check_active_avatar] Активный аватар не найден/не готов для user_id={user_id}")
            text = safe_escape_markdown("🚫 Сначала выбери или создай активный аватар в 'Личный кабинет' -> 'Мои аватары'!")
            reply_markup = await create_user_profile_keyboard(user_id)
            await send_message_with_fallback(bot, user_id, text, reply_markup=reply_markup)
            return None

        logger.debug(f"[check_active_avatar] Найден активный аватар для user_id={user_id}: ID {trained_model[0]}")
        return trained_model

    except Exception as e:
        logger.error(f"[check_active_avatar] Ошибка проверки активного аватара user_id={user_id}: {e}", exc_info=True)
        text = safe_escape_markdown("❌ Ошибка сервера при проверке аватара!")
        reply_markup = await create_main_menu_keyboard(user_id)
        await send_message_with_fallback(bot, user_id, text, reply_markup=reply_markup)
        return None

def check_style_config(style_type: str) -> bool:
    """
    Проверяет корректность конфигурации стилей.
    """
    from generation_config import (
        NEW_MALE_AVATAR_STYLES, NEW_FEMALE_AVATAR_STYLES
    )
    from style import new_male_avatar_prompts, new_female_avatar_prompts

    config_map = {
        'new_male_avatar': (NEW_MALE_AVATAR_STYLES, new_male_avatar_prompts),
        'new_female_avatar': (NEW_FEMALE_AVATAR_STYLES, new_female_avatar_prompts),
    }

    if style_type not in config_map:
        if style_type == 'generic_avatar':
            logger.info(f"Тип стиля '{style_type}' больше не используется, пропускаем проверку")
            return True

        logger.error(f"Неизвестный тип стиля '{style_type}' в check_style_config")
        return False

    style_dict, prompt_dict_for_type = config_map[style_type]

    if not (style_dict and isinstance(style_dict, dict) and len(style_dict) > 0):
        logger.error(f"Словарь стилей для '{style_type}' ({type(style_dict).__name__}) отсутствует/пуст или не является словарем в config.py")
        return False

    if not (prompt_dict_for_type and isinstance(prompt_dict_for_type, dict) and len(prompt_dict_for_type) > 0):
        logger.error(f"Словарь промтов для '{style_type}' ({type(prompt_dict_for_type).__name__}) отсутствует/пуст или не является словарем в config.py")
        return False

    missing_keys = [key for key in style_dict if key not in prompt_dict_for_type]
    if missing_keys:
        logger.error(f"Для '{style_type}' отсутствуют промты для ключей: {missing_keys} в соответствующем словаре промтов.")
        return False

    return True

async def create_payment_link(user_id: int, email: str, amount_value: float, description: str, bot_username: str) -> str:
    """
    Создает ссылку на оплату через YooKassa.
    """
    logger.debug(f"create_payment_link вызван: user_id={user_id}, email={email}, amount={amount_value}, description={description}, bot_username={bot_username}")

    if not YOOKASSA_AVAILABLE:
        logger.error(f"YooKassa недоступна для user_id={user_id}: библиотека не установлена")
        return f"https://test.payment.link/user_id={user_id}&amount={amount_value}"

    if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
        logger.error(f"YooKassa не настроена для user_id={user_id}: YOOKASSA_SHOP_ID={YOOKASSA_SHOP_ID}, YOOKASSA_SECRET_KEY={'***' if YOOKASSA_SECRET_KEY else None}")
        return f"https://test.payment.link/user_id={user_id}&amount={amount_value}"

    try:
        YooKassaConfiguration.account_id = YOOKASSA_SHOP_ID
        YooKassaConfiguration.secret_key = YOOKASSA_SECRET_KEY
        idempotency_key = str(uuid.uuid4())
        logger.debug(f"Инициализация YooKassa: account_id={YOOKASSA_SHOP_ID}, idempotency_key={idempotency_key}")

        payment = YooKassaPayment.create({
            "amount": {
                "value": f"{amount_value:.2f}",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": f"https://t.me/{bot_username.lstrip('@')}"
            },
            "capture": True,
            "description": description[:128],
            "metadata": {
                "user_id": str(user_id),
                "description_for_user": description[:128]
            },
            "receipt": {
                "customer": {"email": email},
                "items": [{
                    "description": description[:128],
                    "quantity": "1.00",
                    "amount": {
                        "value": f"{amount_value:.2f}",
                        "currency": "RUB"
                    },
                    "vat_code": "1",
                    "payment_subject": "service",
                    "payment_mode": "full_payment"
                }]
            }
        }, idempotency_key)

        if not hasattr(payment, 'confirmation') or not hasattr(payment.confirmation, 'confirmation_url'):
            logger.error(f"Некорректный ответ YooKassa для user_id={user_id}: payment={payment}")
            return f"https://test.payment.link/user_id={user_id}&amount={amount_value}"

        logger.info(f"Платёж YooKassa успешно создан: ID={payment.id}, URL={payment.confirmation.confirmation_url}, user_id={user_id}")
        return payment.confirmation.confirmation_url

    except Exception as e:
        logger.error(f"Ошибка создания платежа YooKassa для user_id={user_id}, amount={amount_value}: {e}", exc_info=True)
        return f"https://test.payment.link/user_id={user_id}&amount={amount_value}"

def test_markdown_escaping():
    """
    Тестовая функция для проверки корректности экранирования.
    """
    test_cases = [
        "Sh.Ai.ProTech (@ShAIPro)",
        "user@example.com",
        "ID: 123456789",
        "Balance: $10.50",
        "Text with (parentheses) and [brackets]",
        "Special chars: !@#$%^&*()_+-={}[]|\\:;\"'<>?,./",
    ]

    for test_text in test_cases:
        escaped = safe_escape_markdown(test_text)
        print(f"Original: {test_text}")
        print(f"Escaped:  {escaped}")
        print("---")

def debug_markdown_text(text: str) -> str:
    """
    Отладочная функция для анализа проблемных текстов с Markdown.
    """
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    found_chars = []

    for char in special_chars:
        if char in text and f'\\{char}' not in text:
            found_chars.append(char)

    if found_chars:
        logger.debug(f"Найдены неэкранированные символы: {found_chars}")
        logger.debug(f"Текст: {text[:200]}...")

    return text

def escape_message_parts(*parts: str, version: int = 2) -> str:

    if not parts:
        return ""

    escaped_parts = [safe_escape_markdown(str(part), version=version) for part in parts]
    result = "".join(escaped_parts)
    logger.debug(f"escape_message_parts: объединено {len(parts)} частей, результат: {result[:200]}...")
    return result

def unescape_markdown(text: str) -> str:

    if not text:
        return ""

    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(f'\\{char}', char)
    logger.debug(f"unescape_markdown: очищенный текст: {text[:200]}...")
    return text
