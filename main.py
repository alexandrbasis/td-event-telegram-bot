import logging
from logging.handlers import RotatingFileHandler
import re
from typing import List, Dict, Optional
from dataclasses import asdict
import time
import traceback
from datetime import datetime
from collections import defaultdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from functools import wraps
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
import config
from config import BOT_TOKEN, BOT_USERNAME, COORDINATOR_IDS, VIEWER_IDS
from utils.decorators import require_role
from utils.cache import load_reference_data
from utils.timeouts import set_edit_timeout, clear_expired_edit
from utils.user_logger import UserActionLogger
from database import init_database
from repositories.participant_repository import SqliteParticipantRepository
from repositories.airtable_participant_repository import AirtableParticipantRepository

try:
    from pyairtable.api.exceptions import AirtableApiError

    AIRTABLE_AVAILABLE = True
except ImportError:
    AIRTABLE_AVAILABLE = False
    AirtableApiError = Exception  # Fallback
from services.participant_service import ParticipantService, SearchResult
from models.participant import Participant
from parsers.participant_parser import (
    parse_participant_data,
    is_template_format,
    parse_template_format,
    parse_unstructured_text,
    normalize_field_value,
)
from services.participant_service import (
    merge_participant_data,
    format_participant_block,
    detect_changes,
    update_single_field,
    get_edit_keyboard,
    FIELD_LABELS,
    get_gender_selection_keyboard,
    get_gender_selection_keyboard_simple,
    get_role_selection_keyboard,
    get_size_selection_keyboard,
    get_department_selection_keyboard,
    get_gender_selection_keyboard_required,
    get_size_selection_keyboard_required,
    get_role_selection_keyboard_required,
    get_department_selection_keyboard_required,
)
from utils.validators import validate_participant_data
from utils.exceptions import (
    BotException,
    ParticipantNotFoundError,
    ValidationError,
    DatabaseError,
)
from messages import MESSAGES
from constants import GENDER_DISPLAY, ROLE_DISPLAY, DEPARTMENT_DISPLAY
from states import (
    CONFIRMING_DATA,
    CONFIRMING_DUPLICATE,
    COLLECTING_DATA,
    FILLING_MISSING_FIELDS,
    RECOVERING,
    SEARCHING_PARTICIPANTS,
    SELECTING_PARTICIPANT,
    CHOOSING_ACTION,
    EXECUTING_ACTION,
)

BOT_VERSION = "0.1"


def smart_cleanup_on_error(func):
    """
    Улучшенный декоратор для обработки ошибок с умной очисткой состояния.

    Логика:
    - ValidationError, ParticipantNotFoundError → сохраняем состояние
    - DatabaseError, BotException → очищаем состояние
    - Неизвестные ошибки → очищаем состояние
    """

    @wraps(func)
    async def wrapper(
        update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
    ):
        user_id = update.effective_user.id if update.effective_user else "unknown"
        timestamp = datetime.utcnow().isoformat()

        try:
            return await func(update, context, *args, **kwargs)

        except ValidationError as e:
            # Ошибки валидации - остаёмся в текущем состоянии
            logging.getLogger("errors").warning(
                f"Validation error for user {user_id} in {func.__name__}: {e}",
                exc_info=True,
            )
            user_logger.log_error_with_context(
                user_id,
                e,
                {
                    "user_data": dict(context.user_data),
                    "last_actions": context.user_data.get("action_history", []),
                    "timestamp": timestamp,
                    "bot_version": BOT_VERSION,
                },
                func.__name__,
            )
            try:
                if update.message:
                    await update.message.reply_text(
                        f"❌ **Ошибка валидации:**\n{e}", parse_mode="Markdown"
                    )
                elif update.callback_query:
                    await update.callback_query.answer()
                    await update.callback_query.message.reply_text(
                        f"❌ **Ошибка валидации:**\n{e}", parse_mode="Markdown"
                    )
            except Exception as send_error:
                logger.error(
                    f"Failed to send validation error to user {user_id}: {send_error}"
                )

            # Возвращаем текущее состояние - НЕ завершаем разговор
            current_state = context.user_data.get("current_state", CONFIRMING_DATA)
            return current_state

        except ParticipantNotFoundError as e:
            # Участник не найден - остаёмся в состоянии
            logging.getLogger("errors").warning(
                f"Participant not found for user {user_id} in {func.__name__}: {e}",
                exc_info=True,
            )
            user_logger.log_error_with_context(
                user_id,
                e,
                {
                    "user_data": dict(context.user_data),
                    "last_actions": context.user_data.get("action_history", []),
                    "timestamp": timestamp,
                    "bot_version": BOT_VERSION,
                },
                func.__name__,
            )
            try:
                if update.message:
                    await update.message.reply_text(
                        f"❌ **Участник не найден:**\n{e}", parse_mode="Markdown"
                    )
                elif update.callback_query:
                    await update.callback_query.answer()
                    await update.callback_query.message.reply_text(
                        f"❌ **Участник не найден:**\n{e}", parse_mode="Markdown"
                    )
            except Exception as send_error:
                logger.error(
                    f"Failed to send not found error to user {user_id}: {send_error}"
                )

            return CONFIRMING_DATA

        except AttributeError as e:
            if "job_queue" in str(e) or "run_once" in str(e):
                logging.getLogger("errors").error(
                    f"JobQueue error for user {user_id}: {e}", exc_info=True
                )
                user_logger.log_error_with_context(
                    user_id,
                    e,
                    {
                        "user_data": dict(context.user_data),
                        "last_actions": context.user_data.get("action_history", []),
                        "timestamp": timestamp,
                        "bot_version": BOT_VERSION,
                    },
                    func.__name__,
                )
                return await recover_from_technical_error(update, context)
            raise

        except (DatabaseError, BotException) as e:
            # Серьёзные ошибки - очищаем состояние
            logging.getLogger("errors").error(
                f"Critical error for user {user_id} in {func.__name__}: {type(e).__name__}: {e}",
                exc_info=True,
            )
            user_logger.log_error_with_context(
                user_id,
                e,
                {
                    "user_data": dict(context.user_data),
                    "last_actions": context.user_data.get("action_history", []),
                    "timestamp": timestamp,
                    "bot_version": BOT_VERSION,
                },
                func.__name__,
            )
            cleanup_user_data_safe(
                context, user_id if isinstance(user_id, int) else None
            )

            try:
                if update.message:
                    await update.message.reply_text(
                        "❌ **Произошла техническая ошибка.**\n\n"
                        "🔄 Попробуйте снова с команды /add\n"
                        "📞 Если проблема повторяется, обратитесь к администратору.",
                        parse_mode="Markdown",
                    )
                elif update.callback_query:
                    await update.callback_query.answer()
                    await update.callback_query.message.reply_text(
                        "❌ **Произошла техническая ошибка.**\n\n"
                        "🔄 Попробуйте снова с команды /add",
                        parse_mode="Markdown",
                    )
            except Exception as send_error:
                logging.getLogger("errors").error(
                    f"Failed to send critical error message to user {user_id}: {send_error}"
                )

            return ConversationHandler.END

        except Exception as e:
            # Неизвестные ошибки - очищаем состояние для безопасности
            logging.getLogger("errors").error(
                f"Unexpected error for user {user_id} in {func.__name__}: {type(e).__name__}: {e}",
                exc_info=True,
            )
            user_logger.log_error_with_context(
                user_id,
                e,
                {
                    "user_data": dict(context.user_data),
                    "last_actions": context.user_data.get("action_history", []),
                    "timestamp": timestamp,
                    "bot_version": BOT_VERSION,
                },
                func.__name__,
            )
            cleanup_user_data_safe(
                context, user_id if isinstance(user_id, int) else None
            )

            try:
                if update.message:
                    await update.message.reply_text(
                        "❌ **Произошла неожиданная ошибка.**\n\n"
                        "🔄 Попробуйте снова с команды /add\n"
                        "📞 Если проблема повторяется, обратитесь к администратору.",
                        parse_mode="Markdown",
                    )
                elif update.callback_query:
                    await update.callback_query.answer()
                    await update.callback_query.message.reply_text(
                        "❌ **Произошла неожиданная ошибка.**\n\n"
                        "🔄 Попробуйте снова с команды /add",
                        parse_mode="Markdown",
                    )
            except Exception as send_error:
                logging.getLogger("errors").error(
                    f"Failed to send unexpected error message to user {user_id}: {send_error}"
                )

            return ConversationHandler.END

    return wrapper


def cleanup_on_error(func):
    """Декоратор для автоматической очистки состояния пользователя при ошибках."""

    @wraps(func)
    async def wrapper(
        update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
    ):
        try:
            return await func(update, context, *args, **kwargs)
        except Exception as e:
            user_id = update.effective_user.id if update.effective_user else "unknown"
            logger.error(
                f"Error in {func.__name__} for user {user_id}: {type(e).__name__}: {e}",
                exc_info=True,
            )

            cleanup_user_data_safe(context, update.effective_user.id)
            logger.info(
                f"Cleared user_data for user {user_id} due to error in {func.__name__}"
            )

            try:
                if update.message:
                    await update.message.reply_text(
                        "❌ **Произошла ошибка при обработке данных.**\n\n"
                        "🔄 Попробуйте снова с команды /add\n"
                        "📞 Если проблема повторяется, обратитесь к администратору.",
                        parse_mode="Markdown",
                    )
                elif update.callback_query:
                    await update.callback_query.answer()
                    await update.callback_query.message.reply_text(
                        "❌ **Произошла ошибка при обработке данных.**\n\n"
                        "🔄 Попробуйте снова с команды /add",
                        parse_mode="Markdown",
                    )
            except Exception as send_error:
                logger.error(
                    f"Failed to send error message to user {user_id}: {send_error}"
                )

            return ConversationHandler.END

    return wrapper


def cleanup_user_data_safe(context: ContextTypes.DEFAULT_TYPE, user_id: int = None):
    """Безопасная очистка user_data с логированием."""

    if context.user_data:
        keys_to_clear = list(context.user_data.keys())
        context.user_data.clear()
        logger.info(
            f"Manually cleared user_data for user {user_id or 'unknown'}: removed keys {keys_to_clear}"
        )
    else:
        logger.debug(f"user_data already empty for user {user_id or 'unknown'}")


# --- Вспомогательные функции для очистки ---


def _add_message_to_cleanup(context: ContextTypes.DEFAULT_TYPE, message_id: int):
    """Добавляет ID сообщения в список для последующей очистки."""
    if "messages_to_delete" not in context.user_data:
        context.user_data["messages_to_delete"] = []
    context.user_data["messages_to_delete"].append(message_id)


async def _cleanup_messages(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Удаляет все сообщения, сохраненные для очистки."""
    messages_to_delete = context.user_data.get("messages_to_delete", [])
    for message_id in messages_to_delete:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception as e:
            logger.warning("Could not delete message %d: %s", message_id, e)

    if "messages_to_delete" in context.user_data:
        context.user_data["messages_to_delete"].clear()


async def clear_field_to_edit(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Removes stale field editing context for a user."""
    if context.job:
        user_id = context.job.data
        user_data = context.application.user_data.get(user_id, {})
    else:
        user_id = None
        user_data = context.user_data
    if user_data.pop("field_to_edit", None):
        logger.info("Cleared stale field_to_edit for user %s", user_id)
    job = user_data.pop("clear_edit_job", None)
    if job:
        job.schedule_removal()
    user_data.pop("edit_timeout", None)


def safe_create_timeout_job(
    context: ContextTypes.DEFAULT_TYPE, callback, timeout: int, user_id: int
):
    """Safely create a timeout job if JobQueue is available."""
    if context.job_queue:
        return context.job_queue.run_once(callback, timeout, data=user_id)
    logger.warning(f"JobQueue not available for user {user_id}")
    set_edit_timeout(context, user_id, timeout)
    return None


def _get_recover_edit_keyboard() -> InlineKeyboardMarkup:
    """Keyboard offering to resume editing after a technical issue."""
    keyboard = [
        [
            InlineKeyboardButton(
                "\ud83d\udd04 \u041f\u0440\u043e\u0434\u043e\u043b\u0436\u0438\u0442\u044c \u0440\u0435\u0434\u0430\u043a\u0442\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435",
                callback_data="continue_editing",
            )
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_recovery_keyboard(context: ContextTypes.DEFAULT_TYPE) -> InlineKeyboardMarkup:
    """Keyboard for restoring the dialog after a technical issue."""
    buttons = []
    if context.user_data.get("parsed_participant"):
        buttons.append(
            [
                InlineKeyboardButton(
                    "\U0001f4dd \u041a \u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u0438\u044e",
                    callback_data="recover_confirmation",
                )
            ]
        )
    if context.user_data.get("add_flow_data"):
        buttons.append(
            [
                InlineKeyboardButton(
                    "\u2795 \u041f\u0440\u043e\u0434\u043e\u043b\u0436\u0438\u0442\u044c \u0432\u0432\u043e\u0434",
                    callback_data="recover_input",
                )
            ]
        )
    buttons.append(
        [
            InlineKeyboardButton(
                "\ud83d\udd04 \u041d\u0430\u0447\u0430\u0442\u044c \u0437\u0430\u043d\u043e\u0432\u043e",
                callback_data="main_add",
            )
        ]
    )
    return InlineKeyboardMarkup(buttons)


async def show_recovery_options(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Display recovery choices to the user."""
    keyboard = get_recovery_keyboard(context)
    try:
        msg = await update.effective_message.reply_text(
            "\u26a0\ufe0f \u0422\u0435\u0445\u043d\u0438\u0447\u0435\u0441\u043a\u0430\u044f \u043f\u0440\u043e\u0431\u043b\u0435\u043c\u0430. \u041a\u0430\u043a \u0434\u0435\u0439\u0441\u0442\u0432\u043e\u0432\u0430\u0442\u044c?",
            reply_markup=keyboard,
        )
    except Exception as send_error:  # pragma: no cover - just log
        logger.error(
            "Failed to show recovery options to user %s: %s",
            update.effective_user.id if update.effective_user else "unknown",
            send_error,
        )
    else:
        _add_message_to_cleanup(context, msg.message_id)
    context.user_data["current_state"] = RECOVERING
    return RECOVERING


async def recover_from_technical_error(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Show technical error notice and present recovery options."""
    try:
        if update.callback_query:
            await update.callback_query.answer()
        return await show_recovery_options(update, context)
    except Exception as send_error:  # pragma: no cover - just log
        logger.error(
            "Failed to recover from technical error for user %s: %s",
            update.effective_user.id if update.effective_user else "unknown",
            send_error,
        )
        return context.user_data.get("current_state", CONFIRMING_DATA)


# --- Конец вспомогательных функций ---


# Настройка логирования
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def setup_logging() -> None:
    """Configure logging and separate log files."""
    import os

    # Создаем папку logs если её нет
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    bot_handler = RotatingFileHandler(
        f"{log_dir}/bot.log", maxBytes=10 * 1024 * 1024, backupCount=5
    )
    bot_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    error_handler = RotatingFileHandler(
        f"{log_dir}/errors.log", maxBytes=5 * 1024 * 1024, backupCount=5
    )
    error_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    participant_handler = RotatingFileHandler(
        f"{log_dir}/participant_changes.log", maxBytes=5 * 1024 * 1024, backupCount=5
    )
    participant_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    performance_handler = RotatingFileHandler(
        f"{log_dir}/performance.log", maxBytes=5 * 1024 * 1024, backupCount=5
    )
    performance_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    sql_handler = RotatingFileHandler(
        f"{log_dir}/sql.log", maxBytes=10 * 1024 * 1024, backupCount=5
    )
    sql_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    logging.basicConfig(level=logging.INFO, handlers=[bot_handler], format=LOG_FORMAT)

    logging.getLogger("errors").addHandler(error_handler)
    logging.getLogger("errors").setLevel(logging.ERROR)

    logging.getLogger("participant_changes").addHandler(participant_handler)
    logging.getLogger("participant_changes").setLevel(logging.INFO)

    logging.getLogger("performance").addHandler(performance_handler)
    logging.getLogger("performance").setLevel(logging.INFO)

    sql_logger = logging.getLogger("sql")
    sql_logger.addHandler(sql_handler)
    sql_logger.setLevel(logging.WARNING)


setup_logging()

user_logger = UserActionLogger()
logger = logging.getLogger(__name__)
ERROR_STATS: Dict[str, int] = defaultdict(int)


# helper to keep last user actions
def _record_action(context: ContextTypes.DEFAULT_TYPE, action: str) -> None:
    history = context.user_data.setdefault("action_history", [])
    history.append({"action": action, "timestamp": time.time()})
    if len(history) > 5:
        context.user_data["action_history"] = history[-5:]


def _log_session_end(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    start = context.user_data.pop("session_start", None)
    if start:
        duration = (datetime.utcnow() - start).total_seconds()
        user_logger.log_user_action(user_id, "session_end", {"duration": duration})


def log_state_transitions(func):
    """Decorator to log state transitions for conversation handlers."""

    @wraps(func)
    async def wrapper(
        update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
    ):
        user_id = update.effective_user.id if update.effective_user else "unknown"
        from_state = str(context.user_data.get("current_state"))
        start = time.time()
        data = ""
        msg = getattr(update, "message", None)
        if msg and getattr(msg, "text", None):
            data = msg.text
        else:
            cq = getattr(update, "callback_query", None)
            if cq and getattr(cq, "data", None):
                data = cq.data
        try:
            next_state = await func(update, context, *args, **kwargs)
            duration = time.time() - start
            user_logger.log_state_transition(
                user_id,
                from_state,
                str(next_state),
                {"input": data, "duration": duration},
            )
            _record_action(context, f"state:{func.__name__}")
            return next_state
        except Exception as e:
            user_logger.log_error_with_context(
                user_id,
                e,
                {
                    "user_data": dict(context.user_data),
                    "last_actions": context.user_data.get("action_history", []),
                    "input": data,
                    "timestamp": datetime.utcnow().isoformat(),
                },
                func.__name__,
            )
            raise

    return wrapper


async def log_all_updates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Middleware to log every incoming update."""
    logger.info("Incoming update: %s", update.to_dict())


# Timeout in seconds to wait for user input when editing a specific field
FIELD_EDIT_TIMEOUT = 300

# Initialize repository and service instances
participant_repository = None
participant_service = None

# --- REQUIRED AND OPTIONAL FIELDS ---
REQUIRED_FIELDS = ["FullNameRU", "Gender", "Size", "Church", "Role"]
OPTIONAL_FIELDS = [
    "FullNameEN",
    "CountryAndCity",
    "SubmittedBy",
    "ContactInformation",
    "Department",
]

# Field to keyboard mapping for interactive prompts during /add flow
FIELD_KEYBOARDS = {
    "Gender": get_gender_selection_keyboard_required,
    "Size": get_size_selection_keyboard_required,
    "Role": get_role_selection_keyboard_required,
    "Department": get_department_selection_keyboard_required,
}


# Функция проверки прав пользователя
def get_user_role(user_id):
    if user_id in COORDINATOR_IDS:
        return "coordinator"
    elif user_id in VIEWER_IDS:
        return "viewer"
    else:
        return "unauthorized"


async def show_confirmation(
    update: Update, context: ContextTypes.DEFAULT_TYPE, participant_data: Dict
) -> None:
    """Отправляет сообщение с данными участника и клавиатурой для редактирования."""
    user_id = update.effective_user.id
    logger.info(f"Showing confirmation for user {user_id}")
    logger.debug(f"user_data keys: {list(context.user_data.keys())}")
    confirmation_text = "🔍 Вот что удалось распознать. Всё правильно?\n\n"
    confirmation_text += format_participant_block(participant_data)
    confirmation_text += '\n\n✅ Нажмите "Сохранить", чтобы завершить, или выберите поле для исправления.'
    keyboard = get_edit_keyboard(participant_data)
    logger.debug(f"Generated keyboard with {len(keyboard.inline_keyboard)} rows")
    if logger.isEnabledFor(logging.DEBUG):
        for i, row in enumerate(keyboard.inline_keyboard):
            for j, button in enumerate(row):
                logger.debug(
                    f"Button [{i}][{j}]: text='{button.text}', callback_data='{button.callback_data}'"
                )

    message = update.effective_message
    msg = await message.reply_text(
        confirmation_text,
        parse_mode="Markdown",
        reply_markup=keyboard,
    )
    _add_message_to_cleanup(context, msg.message_id)

    # Сохраняем текущее состояние для декоратора
    context.user_data["current_state"] = CONFIRMING_DATA
    context.user_data["filling_missing_field"] = False


def get_duplicate_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for handling duplicate participant decisions."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Добавить новый", callback_data="dup_add_new"),
            InlineKeyboardButton("🔄 Заменить", callback_data="dup_replace"),
        ],
        [InlineKeyboardButton("❌ Отмена", callback_data="main_cancel")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_post_action_keyboard() -> InlineKeyboardMarkup:
    """Keyboard shown after successful add/update."""
    keyboard = [
        [
            InlineKeyboardButton("➕ Добавить еще", callback_data="main_add"),
            InlineKeyboardButton("📋 Список", callback_data="main_list"),
        ],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_no_changes_keyboard() -> InlineKeyboardMarkup:
    """Keyboard shown when no changes were detected during editing."""
    keyboard = [
        [
            InlineKeyboardButton(
                "\ud83d\udd04 \u041f\u0440\u043e\u0434\u043e\u043b\u0436\u0438\u0442\u044c \u0440\u0435\u0434\u0430\u043a\u0442\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u0435",
                callback_data="continue_editing",
            )
        ],
        [
            InlineKeyboardButton(
                "\u2705 \u0421\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c \u043a\u0430\u043a \u0435\u0441\u0442\u044c",
                callback_data="confirm_save",
            )
        ],
        [
            InlineKeyboardButton(
                "\u274c \u041e\u0442\u043c\u0435\u043d\u0438\u0442\u044c",
                callback_data="main_cancel",
            )
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def _get_return_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру с кнопкой возврата в главное меню."""
    keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data="main_menu")]]
    return InlineKeyboardMarkup(keyboard)


async def _send_response_with_menu_button(
    update: Update,
    text: str,
    *,
    parse_mode: str = "Markdown",
) -> None:
    """Reply with text and a 'Return to menu' button for both command and callback handlers."""
    try:
        if update.callback_query:
            await update.callback_query.message.reply_text(
                text,
                parse_mode=parse_mode,
                reply_markup=_get_return_to_menu_keyboard(),
            )
        else:
            await update.message.reply_text(
                text,
                parse_mode=parse_mode,
                reply_markup=_get_return_to_menu_keyboard(),
            )
    except Exception as e:  # pragma: no cover - just log
        logger.error(f"Error sending response with menu button: {e}")
        if update.callback_query:
            await update.callback_query.message.reply_text(text, parse_mode=parse_mode)
        else:
            await update.message.reply_text(text, parse_mode=parse_mode)


# --- HELPER FUNCTIONS (NEW) ---


def get_main_menu_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру главного меню в зависимости от роли пользователя."""

    if user_id in COORDINATOR_IDS:
        keyboard = [
            [
                InlineKeyboardButton("➕ Добавить", callback_data="main_add"),
                InlineKeyboardButton("🔍 Поиск", callback_data="main_search"),
            ],
            [
                InlineKeyboardButton("📋 Список", callback_data="main_list"),
                InlineKeyboardButton("📤 Экспорт", callback_data="main_export"),
            ],
            [InlineKeyboardButton("ℹ️ Помощь", callback_data="main_help")],
        ]
    else:
        keyboard = [
            [
                InlineKeyboardButton("🔍 Поиск", callback_data="main_search"),
                InlineKeyboardButton("📋 Список", callback_data="main_list"),
            ],
            [
                InlineKeyboardButton("📤 Экспорт", callback_data="main_export"),
                InlineKeyboardButton("ℹ️ Помощь", callback_data="main_help"),
            ],
        ]

    return InlineKeyboardMarkup(keyboard)


def get_missing_fields(participant_data: Dict) -> List[str]:
    """Checks for missing required fields."""
    missing = []
    for field in REQUIRED_FIELDS:
        if not participant_data.get(field):
            missing.append(FIELD_LABELS.get(field, field))

    if participant_data.get("Role") == "TEAM" and not participant_data.get(
        "Department"
    ):
        missing.append(FIELD_LABELS.get("Department", "Department"))
    return missing


def safe_merge_participant_data(existing: Dict, updates: Dict) -> Dict:
    """Merge updates without overwriting already filled fields."""
    for key, value in updates.items():
        if not existing.get(key) and value:
            existing[key] = value
            if key == "Role":
                if value == "TEAM" and "Department" not in updates:
                    existing["Department"] = ""
    return existing


def get_missing_field_keys(participant_data: Dict) -> List[str]:
    """Return field names that are still empty."""
    missing = []
    for field in REQUIRED_FIELDS:
        if not participant_data.get(field):
            missing.append(field)
    if participant_data.get("Role") == "TEAM" and not participant_data.get(
        "Department"
    ):
        missing.append("Department")
    return missing


def get_next_missing_field(participant_data: Dict) -> Optional[str]:
    """Return the next missing field or ``None`` if all filled."""
    missing = get_missing_field_keys(participant_data)
    return missing[0] if missing else None


async def show_interactive_missing_field(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    participant_data: Dict,
) -> None:
    """Prompt user to fill the next missing field showing the keyboard if available."""

    # Mark that we are in the context of filling missing fields
    context.user_data["filling_missing_field"] = True

    field = get_next_missing_field(participant_data)
    if not field:
        return

    context.user_data["waiting_for_field"] = field

    cancel_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton("❌ Отмена", callback_data="main_cancel")]]
    )

    message = update.effective_message
    keyboard_func = FIELD_KEYBOARDS.get(field)
    if keyboard_func:
        kb = keyboard_func()
        msg = await message.reply_text(
            f"Выберите значение для поля **{FIELD_LABELS.get(field, field)}**",
            parse_mode="Markdown",
            reply_markup=kb,
        )
    else:
        msg = await message.reply_text(
            f"Пришлите значение для поля **{FIELD_LABELS.get(field, field)}**",
            parse_mode="Markdown",
            reply_markup=cancel_markup,
        )
    _add_message_to_cleanup(context, msg.message_id)


def format_status_message(participant_data: Dict) -> str:
    """Creates a status message with filled data and missing fields."""
    message = "📝 **Процесс добавления:**\n\n"
    message += format_participant_block(participant_data)
    message += "\n\n"

    missing = get_missing_fields(participant_data)
    if missing:
        message += "🔴 **Осталось заполнить:**\n- " + "\n- ".join(missing)
        message += "\n\nОтправьте данные для одного из этих полей или отправьте /cancel для отмены."
    else:
        message += "✅ **Все обязательные поля заполнены!**\n\n"
        message += "Отправьте **ДА** для подтверждения или **НЕТ** для отмены."

    return message


async def _show_main_menu(
    update: Update, context: ContextTypes.DEFAULT_TYPE, is_return: bool = False
) -> None:
    """Display the main menu, editing the existing message when possible."""
    user_id = update.effective_user.id
    role = get_user_role(user_id)

    if is_return:
        welcome_text = (
            "✅ **Операция завершена.**\n\n" "Чем еще я могу для вас сделать?"
        )
    else:
        welcome_text = (
            "🏕️ **Добро пожаловать в бот Tres Dias Israel!**\n\n"
            f"👤 Ваша роль: **{role.title()}**"
        )
    reply_markup = get_main_menu_keyboard(user_id)

    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(
                text=welcome_text,
                parse_mode="Markdown",
                reply_markup=reply_markup,
            )
        except Exception:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=welcome_text,
                parse_mode="Markdown",
                reply_markup=reply_markup,
            )
    else:
        await update.effective_message.reply_text(
            text=welcome_text,
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )


# Команда /start
@require_role("viewer")
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point that shows the main menu."""
    user_id = update.effective_user.id
    _log_session_end(context, user_id)
    context.user_data["session_start"] = datetime.utcnow()
    user_logger.log_user_action(user_id, "command_start", {"command": "/start"})
    _record_action(context, "/start:start")

    logger.info("User %s started /start", user_id)
    await _cleanup_messages(context, update.effective_chat.id)
    await _show_main_menu(update, context)
    user_logger.log_user_action(user_id, "command_end", {"command": "/start"})


@require_role("coordinator")
async def handle_add_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Starts the add flow from the main menu button."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_reply_markup(reply_markup=None)

    context.user_data["add_flow_data"] = {
        "FullNameRU": None,
        "Gender": None,
        "Size": None,
        "Church": None,
        "Role": None,
        "Department": None,
        "FullNameEN": None,
        "CountryAndCity": None,
        "SubmittedBy": None,
        "ContactInformation": None,
    }

    cancel_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton("❌ Отмена", callback_data="main_cancel")]]
    )

    msg1 = await query.message.reply_text(
        "🚀 **Начинаем добавлять нового участника.**\n\n"
        "Отправьте данные любым удобным способом:\n"
        "1️⃣ **Вставьте заполненный шаблон** (пришлю его следующим сообщением).\n"
        "2️⃣ **Отправьте несколько полей**, разделяя их запятой (`,`) или каждое с новой строкой.\n"
        "3️⃣ **Отправляйте по одному полю** в сообщении (например, `Церковь Грейс`).\n\n"
        "*Для самой точной обработки используйте запятые или ввод с новой строки.*\n"
        "Для отмены введите /cancel.",
        parse_mode="Markdown",
        reply_markup=cancel_markup,
    )
    msg2 = await query.message.reply_text(MESSAGES["ADD_TEMPLATE"])
    _add_message_to_cleanup(context, msg1.message_id)
    _add_message_to_cleanup(context, msg2.message_id)
    _add_message_to_cleanup(context, query.message.message_id)
    context.user_data["current_state"] = COLLECTING_DATA
    return COLLECTING_DATA


@require_role("viewer")
async def handle_main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатия на кнопки главного меню."""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    user_logger.log_user_action(user_id, "menu_action", {"action": data})

    await query.edit_message_reply_markup(reply_markup=None)

    if data == "main_cancel":
        _log_session_end(context, user_id)
        await _cleanup_messages(context, update.effective_chat.id)
        cleanup_user_data_safe(context, user_id)
        await _show_main_menu(update, context, is_return=True)
        return

    if data == "main_menu":
        await _show_main_menu(update, context, is_return=True)
        return

    # main_list mirrors the /list command
    if data == "main_list":
        participants = participant_service.get_all_participants()
        if not participants:
            await query.message.reply_text(
                "📋 **Список участников пуст**\n\nИспользуйте /add для добавления участников.",
                parse_mode="Markdown",
            )
            return

        message = f"📋 **Список участников ({len(participants)} чел.):**\n\n"
        for p in participants:
            role_emoji = "👤" if p.Role == "CANDIDATE" else "👨‍💼"
            department = (
                f" ({p.Department})" if p.Role == "TEAM" and p.Department else ""
            )
            message += f"{role_emoji} **{p.FullNameRU}**\n"
            message += f"   • Роль: {p.Role}{department}\n"
            message += f"   • ID: {p.id}\n\n"

        await _send_response_with_menu_button(update, message)
        return

    # main_export mirrors the /export command
    if data == "main_export":
        await _send_response_with_menu_button(
            update,
            "📤 **Экспорт данных** (заглушка)\n\n"
            "🔧 Функция в разработке.\n"
            "Пример: /export worship team - экспорт участников worship команды",
        )
        return

    # main_help mirrors the /help command
    if data == "main_help":
        help_text = """
📖 **Справка по командам:**

👥 **Управление участниками:**
/add - Добавить нового участника
/edit - Редактировать данные участника
/delete - Удалить участника

📊 **Просмотр данных:**
/list - Показать список участников
/export - Экспорт данных в CSV

❓ **Помощь:**
/help - Показать эту справку
/start - Главное меню
/cancel - Отменить текущую операцию

🔍 **Примеры запросов (скоро):**
"Сколько team-member в worship?"
"Кто живет в комнате 203A?"
        """

        await _send_response_with_menu_button(update, help_text)
        return


# --- SEARCH HANDLERS ---


@require_role("viewer")
async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Инициация поиска участников через команду /search."""

    user_id = update.effective_user.id
    user_logger.log_user_action(user_id, "command_start", {"command": "/search"})
    _record_action(context, "/search:start")

    cancel_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton("❌ Отмена", callback_data="main_cancel")]]
    )

    msg1 = await update.message.reply_text(
        "🔍 **Поиск участников**\n\n"
        "Введите для поиска:\n"
        "• **Имя** (русское или английское)\n"
        "• **ID участника** (например: 123)\n"
        "• **Часть имени** (например: Иван)\n\n"
        "💡 *Поиск поддерживает нечеткое совпадение*",
        parse_mode="Markdown",
        reply_markup=cancel_markup,
    )

    _add_message_to_cleanup(context, msg1.message_id)
    _add_message_to_cleanup(context, update.message.message_id)

    context.user_data["current_state"] = SEARCHING_PARTICIPANTS
    return SEARCHING_PARTICIPANTS


@require_role("viewer")
async def handle_search_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик кнопки поиска из главного меню."""

    query = update.callback_query
    await query.answer()
    await query.edit_message_reply_markup(reply_markup=None)

    cancel_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton("❌ Отмена", callback_data="main_cancel")]]
    )

    msg1 = await query.message.reply_text(
        "🔍 **Поиск участников**\n\n"
        "Введите для поиска:\n"
        "• **Имя** (русское или английское)\n"
        "• **ID участника** (например: 123)\n"
        "• **Часть имени** (например: Иван)\n\n"
        "💡 *Поиск поддерживает нечеткое совпадение*",
        parse_mode="Markdown",
        reply_markup=cancel_markup,
    )

    _add_message_to_cleanup(context, msg1.message_id)
    _add_message_to_cleanup(context, query.message.message_id)

    context.user_data["current_state"] = SEARCHING_PARTICIPANTS
    return SEARCHING_PARTICIPANTS


@smart_cleanup_on_error
@log_state_transitions
async def handle_search_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка поискового запроса."""

    user_id = update.effective_user.id
    query_text = update.message.text.strip()

    if len(query_text) < 2:
        await update.message.reply_text(
            "❌ Слишком короткий запрос. Введите минимум 2 символа."
        )
        return SEARCHING_PARTICIPANTS

    _add_message_to_cleanup(context, update.message.message_id)

    start = time.time()
    search_results = participant_service.search_participants(query_text, max_results=5)
    duration = time.time() - start

    user_logger.log_user_action(
        user_id,
        "search_performed",
        {"query": query_text, "results_count": len(search_results)},
    )
    user_logger.log_search_operation(
        user_id,
        query_text,
        len(search_results),
        duration,
    )

    if not search_results:
        no_results_keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🔍 Новый поиск", callback_data="main_search")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")],
            ]
        )

        msg = await update.message.reply_text(
            f"❌ **Участники не найдены**\n\n"
            f"Поиск по запросу: *{query_text}*\n"
            f"Попробуйте изменить запрос или проверить правильность написания.",
            parse_mode="Markdown",
            reply_markup=no_results_keyboard,
        )
        _add_message_to_cleanup(context, msg.message_id)
        return SEARCHING_PARTICIPANTS

    results_text = (
        f"🔍 **Результаты поиска** (найдено: {len(search_results)})\n\n"
    )
    for result in search_results:
        results_text += participant_service.format_search_result(result) + "\n\n"
    results_text += "👆 Выберите участника для действий:"

    keyboard = get_search_results_keyboard(search_results)
    msg = await update.message.reply_text(
        results_text, parse_mode="Markdown", reply_markup=keyboard
    )
    _add_message_to_cleanup(context, msg.message_id)

    context.user_data["search_results"] = search_results
    context.user_data["current_state"] = SELECTING_PARTICIPANT

    return SELECTING_PARTICIPANT


@smart_cleanup_on_error
async def handle_participant_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Обработка выбора участника из результатов поиска."""

    query = update.callback_query
    await query.answer()

    participant_id = int(query.data.split("_")[-1])
    user_id = update.effective_user.id

    search_results: List[SearchResult] = context.user_data.get("search_results", [])
    selected_participant: Optional[Participant] = None
    for result in search_results:
        if result.participant.id == participant_id:
            selected_participant = result.participant
            break

    if not selected_participant:
        await query.message.reply_text(
            "❌ Участник не найден. Попробуйте поиск снова."
        )
        return SEARCHING_PARTICIPANTS

    user_logger.log_user_action(
        user_id,
        "participant_selected",
        {
            "participant_id": participant_id,
            "participant_name": selected_participant.FullNameRU,
        },
    )

    context.user_data["selected_participant"] = selected_participant

    await show_participant_details_and_actions(update, context, selected_participant)

    context.user_data["current_state"] = CHOOSING_ACTION
    return CHOOSING_ACTION


async def show_participant_details_and_actions(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    participant: Participant,
) -> None:
    """Показывает подробную информацию об участнике и доступные действия."""

    user_id = update.effective_user.id
    is_coordinator = user_id in COORDINATOR_IDS

    details_text = f"👤 **{participant.FullNameRU}** (ID: {participant.id})\n\n"
    if participant.FullNameEN:
        details_text += f"🌍 **English:** {participant.FullNameEN}\n"
    details_text += f"⚥ **Пол:** {GENDER_DISPLAY.get(participant.Gender, participant.Gender)}\n"
    details_text += f"👕 **Размер:** {participant.Size or 'Не указано'}\n"
    details_text += f"⛪ **Церковь:** {participant.Church or 'Не указано'}\n"
    details_text += f"👥 **Роль:** {ROLE_DISPLAY.get(participant.Role, participant.Role)}\n"
    if participant.Role == "TEAM" and participant.Department:
        details_text += (
            f"🏢 **Департамент:** {DEPARTMENT_DISPLAY.get(participant.Department, participant.Department)}\n"
        )
    if participant.CountryAndCity:
        details_text += f"🏙️ **Город:** {participant.CountryAndCity}\n"
    if participant.SubmittedBy:
        details_text += f"👨‍💼 **Кто подал:** {participant.SubmittedBy}\n"
    if participant.ContactInformation:
        details_text += f"📞 **Контакты:** {participant.ContactInformation}\n"
    details_text += (
        f"\n🕐 **Создан:** {getattr(participant, 'created_at', 'Неизвестно')}"
    )

    keyboard = get_participant_actions_keyboard(participant, is_coordinator)

    if update.callback_query:
        msg = await update.callback_query.message.reply_text(
            details_text, parse_mode="Markdown", reply_markup=keyboard
        )
    else:
        msg = await update.message.reply_text(
            details_text, parse_mode="Markdown", reply_markup=keyboard
        )

    _add_message_to_cleanup(context, msg.message_id)


@smart_cleanup_on_error
async def handle_action_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Обработка выбора действия над участником."""

    query = update.callback_query
    await query.answer()

    action = query.data
    user_id = update.effective_user.id
    selected_participant: Optional[Participant] = context.user_data.get(
        "selected_participant"
    )

    if not selected_participant:
        await query.message.reply_text(
            "❌ Участник не выбран. Начните поиск заново."
        )
        return ConversationHandler.END

    participant_id = selected_participant.id
    participant_name = selected_participant.FullNameRU

    if action == "action_edit":
        if user_id not in COORDINATOR_IDS:
            await query.message.reply_text(
                "❌ Только координаторы могут редактировать участников."
            )
            return CHOOSING_ACTION

        context.user_data["participant_id"] = participant_id
        context.user_data["parsed_participant"] = asdict(selected_participant)

        user_logger.log_user_action(
            user_id,
            "edit_initiated",
            {"participant_id": participant_id},
        )

        await show_confirmation(update, context, asdict(selected_participant))
        return CONFIRMING_DATA

    if action == "action_delete":
        if user_id not in COORDINATOR_IDS:
            await query.message.reply_text(
                "❌ Только координаторы могут удалять участников."
            )
            return CHOOSING_ACTION

        confirm_keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ Да, удалить", callback_data=f"confirm_delete_{participant_id}"
                    ),
                    InlineKeyboardButton("❌ Отмена", callback_data="action_cancel"),
                ]
            ]
        )

        await query.message.reply_text(
            f"⚠️ **Подтверждение удаления**\n\n"
            f"Вы действительно хотите удалить участника:\n"
            f"**{participant_name}** (ID: {participant_id})?\n\n"
            f"❗ *Это действие нельзя отменить.*",
            parse_mode="Markdown",
            reply_markup=confirm_keyboard,
        )
        return EXECUTING_ACTION

    if action.startswith("confirm_delete_"):
        participant_id = int(action.split("_")[-1])
        try:
            participant_service.delete_participant(
                participant_id,
                user_id=user_id,
                reason="Manual deletion via search",
            )
            user_logger.log_participant_action(
                user_id, "participant_deleted", participant_id, {}
            )
            success_keyboard = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("🔍 Новый поиск", callback_data="main_search")],
                    [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")],
                ]
            )
            await query.message.reply_text(
                f"✅ **Участник удален**\n\n"
                f"**{participant_name}** (ID: {participant_id}) успешно удален из базы данных.",
                parse_mode="Markdown",
                reply_markup=success_keyboard,
            )
        except Exception as e:  # pragma: no cover - log error
            logger.error(f"Error deleting participant {participant_id}: {e}")
            await query.message.reply_text(
                f"❌ **Ошибка при удалении**\n\n"
                f"Не удалось удалить участника {participant_name}. Попробуйте позже."
            )

        cleanup_user_data_safe(context, user_id)
        return ConversationHandler.END

    if action == "action_cancel":
        await show_participant_details_and_actions(
            update, context, selected_participant
        )
        return CHOOSING_ACTION

    if action == "search_new":
        cleanup_user_data_safe(context, user_id)
        return await handle_search_callback(update, context)

    return CHOOSING_ACTION


def get_search_results_keyboard(results: List[SearchResult]) -> InlineKeyboardMarkup:
    """Создает клавиатуру с результатами поиска (максимум 5 кнопок)."""

    buttons: List[List[InlineKeyboardButton]] = []
    for result in results[:5]:
        participant = result.participant
        confidence_emoji = "🎯" if result.confidence == 1.0 else "🔍"
        role_emoji = "👤" if participant.Role == "CANDIDATE" else "👨‍💼"
        button_text = f"{confidence_emoji} {role_emoji} {participant.FullNameRU}"
        if len(button_text) > 30:
            button_text = button_text[:27] + "..."

        buttons.append(
            [
                InlineKeyboardButton(
                    button_text,
                    callback_data=f"select_participant_{participant.id}",
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton("🔍 Новый поиск", callback_data="main_search"),
            InlineKeyboardButton("❌ Отмена", callback_data="main_cancel"),
        ]
    )

    return InlineKeyboardMarkup(buttons)


def get_participant_actions_keyboard(
    participant: Participant, is_coordinator: bool
) -> InlineKeyboardMarkup:
    """Создает клавиатуру с доступными действиями."""

    buttons: List[List[InlineKeyboardButton]] = []
    if is_coordinator:
        buttons.extend(
            [
                [
                    InlineKeyboardButton(
                        "✏️ Редактировать", callback_data="action_edit"
                    ),
                    InlineKeyboardButton(
                        "🗑️ Удалить", callback_data="action_delete"
                    ),
                ],
                [
                    InlineKeyboardButton("🔍 Новый поиск", callback_data="search_new"),
                    InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"),
                ],
            ]
        )
    else:
        buttons.append(
            [
                InlineKeyboardButton("🔍 Новый поиск", callback_data="search_new"),
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"),
            ]
        )

    return InlineKeyboardMarkup(buttons)

# Equivalent to the main_help callback handler
# Команда /help
@require_role("viewer")
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_logger.log_user_action(user_id, "command_start", {"command": "/help"})
    _record_action(context, "/help:start")
    role = get_user_role(user_id)
    logger.info("User %s requested help", user_id)

    help_text = """
📖 **Справка по командам:**

👥 **Управление участниками:**
/add - Добавить нового участника
/edit - Редактировать данные участника
/delete - Удалить участника

📊 **Просмотр данных:**
/list - Показать список участников
/export - Экспорт данных в CSV

❓ **Помощь:**
/help - Показать эту справку
/start - Главное меню
/cancel - Отменить текущую операцию

🔍 **Примеры запросов (скоро):**
"Сколько team-member в worship?"
"Кто живет в комнате 203A?"
    """

    await _send_response_with_menu_button(update, help_text)
    user_logger.log_user_action(user_id, "command_end", {"command": "/help"})


# Команда /add
@require_role("coordinator")
@cleanup_on_error
async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the /add flow and initializes the session."""
    user_id = update.effective_user.id
    user_logger.log_user_action(user_id, "command_start", {"command": "/add"})
    _record_action(context, "/add:start")

    context.user_data["add_flow_data"] = {
        "FullNameRU": None,
        "Gender": None,
        "Size": None,
        "Church": None,
        "Role": None,
        "Department": None,
        "FullNameEN": None,
        "CountryAndCity": None,
        "SubmittedBy": None,
        "ContactInformation": None,
    }

    cancel_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton("❌ Отмена", callback_data="main_cancel")]]
    )

    msg1 = await update.message.reply_text(
        "🚀 **Начинаем добавлять нового участника.**\n\n"
        "Отправьте данные любым удобным способом:\n"
        "1️⃣ **Вставьте заполненный шаблон** (пришлю его следующим сообщением).\n"
        "2️⃣ **Отправьте несколько полей**, разделяя их запятой (`,`) или каждое с новой строки.\n"
        "3️⃣ **Отправляйте по одному полю** в сообщении (например, `Церковь Грейс`).\n\n"
        "*Для самой точной обработки используйте запятые или ввод с новой строки.*\n"
        "Для отмены введите /cancel.",
        parse_mode="Markdown",
        reply_markup=cancel_markup,
    )
    msg2 = await update.message.reply_text(MESSAGES["ADD_TEMPLATE"])
    _add_message_to_cleanup(context, msg1.message_id)
    _add_message_to_cleanup(context, msg2.message_id)
    _add_message_to_cleanup(context, update.message.message_id)
    context.user_data["current_state"] = COLLECTING_DATA
    user_logger.log_state_transition(user_id, "START", str(COLLECTING_DATA), {})
    return COLLECTING_DATA


@require_role("coordinator")
@smart_cleanup_on_error
@log_state_transitions
async def handle_partial_data(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Collects and processes partial data, supporting multiple formats."""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    _add_message_to_cleanup(context, update.message.message_id)
    participant_data = context.user_data.get("add_flow_data", {})

    waiting_field = context.user_data.pop("waiting_for_field", None)
    if waiting_field:
        normalized = normalize_field_value(waiting_field, text)
        participant_data[waiting_field] = normalized or text
        context.user_data["add_flow_data"] = participant_data
        missing_fields = get_missing_field_keys(participant_data)
        if not missing_fields:
            context.user_data["parsed_participant"] = participant_data
            await show_confirmation(update, context, participant_data)
            context.user_data["current_state"] = CONFIRMING_DATA
            return CONFIRMING_DATA
        await show_interactive_missing_field(update, context, participant_data)
        context.user_data["current_state"] = FILLING_MISSING_FIELDS
        return FILLING_MISSING_FIELDS

    # 1. Check if user pasted a full template (highest priority)
    if is_template_format(text):
        parsed_update = parse_template_format(text)
        participant_data = safe_merge_participant_data(participant_data, parsed_update)
    else:
        # 2. Try splitting by newline or comma to detect multiple fields
        chunks = []
        if "\n" in text:
            chunks = [c.strip() for c in text.split("\n") if c.strip()]
        elif "," in text:
            chunks = [c.strip() for c in text.split(",") if c.strip()]
        else:
            chunks = [text]

        # Parse each chunk separately
        for chunk in chunks:
            if not chunk:
                continue

            if ":" in chunk:
                parsed_chunk = parse_participant_data(chunk, is_update=True)
            else:
                parsed_chunk = parse_participant_data(chunk, is_update=False)

            participant_data = safe_merge_participant_data(
                participant_data, parsed_chunk
            )

    # --- NAME DUPLICATE CHECK BLOCK ---
    newly_identified_name = participant_data.get("FullNameRU")
    if newly_identified_name and not context.user_data.get("participant_id"):
        existing_participant = participant_service.check_duplicate(
            newly_identified_name, user_id=user_id
        )
        if existing_participant:
            context.user_data["participant_id"] = existing_participant.id
            existing_dict = asdict(existing_participant)
            context.user_data["add_flow_data"] = existing_dict
            context.user_data["parsed_participant"] = existing_dict
            await update.message.reply_text(
                f"ℹ️ Участник с именем '{newly_identified_name}' уже существует. Переключаюсь в режим редактирования."
            )
            await show_confirmation(update, context, existing_dict)
            return CONFIRMING_DATA

    context.user_data["add_flow_data"] = participant_data

    missing_fields = get_missing_fields(participant_data)

    if not missing_fields:
        context.user_data["parsed_participant"] = participant_data

        logger.info(
            f"User {user_id} parsed participant data: {participant_data.get('FullNameRU', 'Unknown')}"
        )
        logger.debug(f"Saving participant data: {participant_data}")
        logger.debug(f"user_data after save: {context.user_data}")

        await show_confirmation(update, context, participant_data)
        context.user_data["current_state"] = CONFIRMING_DATA
        return CONFIRMING_DATA
    else:
        await show_interactive_missing_field(update, context, participant_data)
        context.user_data["current_state"] = FILLING_MISSING_FIELDS
        return FILLING_MISSING_FIELDS


@require_role("coordinator")
@smart_cleanup_on_error
@log_state_transitions
async def handle_missing_field_input(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handles user input during step-by-step field collection."""
    text = update.message.text.strip()
    _add_message_to_cleanup(context, update.message.message_id)

    participant_data = context.user_data.get("add_flow_data", {})
    waiting_field = context.user_data.pop("waiting_for_field", None)

    if waiting_field:
        normalized = normalize_field_value(waiting_field, text)
        participant_data[waiting_field] = normalized or text
        context.user_data["add_flow_data"] = participant_data

    missing_fields = get_missing_field_keys(participant_data)
    if not missing_fields:
        context.user_data["parsed_participant"] = participant_data
        await show_confirmation(update, context, participant_data)
        context.user_data["current_state"] = CONFIRMING_DATA
        return CONFIRMING_DATA

    await show_interactive_missing_field(update, context, participant_data)
    context.user_data["current_state"] = FILLING_MISSING_FIELDS
    return FILLING_MISSING_FIELDS


# Команда /edit
@require_role("coordinator")
async def edit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    user_logger.log_user_action(user_id, "command_start", {"command": "/edit"})
    _record_action(context, "/edit:start")

    await _send_response_with_menu_button(
        update,
        "✏️ **Редактирование участника** (заглушка)\n\n"
        "🔧 Функция в разработке.\n"
        "Пример: /edit 123 - редактировать участника с ID 123",
    )

    user_logger.log_user_action(
        user_id, "command_end", {"command": "/edit", "result": "not_implemented"}
    )


# Команда /delete
@require_role("coordinator")
async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    user_logger.log_user_action(user_id, "command_start", {"command": "/delete"})
    _record_action(context, "/delete:start")

    await _send_response_with_menu_button(
        update,
        "🗑️ **Удаление участника** (заглушка)\n\n"
        "🔧 Функция в разработке.\n"
        "Пример: /delete 123 - удалить участника с ID 123",
    )

    user_logger.log_user_action(
        user_id, "command_end", {"command": "/delete", "result": "not_implemented"}
    )


@require_role("coordinator")
async def edit_field_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    ✅ НОВАЯ КОМАНДА: Демонстрация частичного обновления полей.

    Использование: /edit_field 123 FullNameRU "Новое имя"
    """
    try:
        parts = update.message.text.split(" ", 3)
        if len(parts) < 4:
            await update.message.reply_text(
                "❌ **Использование:** /edit_field ID поле значение\n\n"
                '**Пример:** /edit_field 123 FullNameRU "Новое имя"',
                parse_mode="Markdown",
            )
            return

        _, participant_id, field_name, new_value = parts
        participant_id = int(participant_id)

        if not participant_service.participant_exists(participant_id):
            await update.message.reply_text(
                f"❌ Участник с ID {participant_id} не найден"
            )
            return

        kwargs = {field_name: new_value}
        success = participant_service.update_participant_fields(
            participant_id, user_id=user_id, **kwargs
        )

        if success:
            user_logger.log_participant_operation(
                user_id, "update_fields", kwargs, participant_id
            )
            await update.message.reply_text(
                f"✅ **Поле обновлено!**\n\n"
                f"🆔 ID: {participant_id}\n"
                f"📝 Поле: {field_name}\n"
                f"🔄 Новое значение: {new_value}",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text("❌ Ошибка при обновлении поля")

    except ValueError as e:
        await update.message.reply_text(f"❌ Ошибка валидации: {e}")
    except ParticipantNotFoundError as e:
        await update.message.reply_text(f"❌ {e}")
    except Exception as e:
        logger.error("Error in edit_field_command: %s", e)
        await update.message.reply_text("❌ Произошла ошибка при обновлении поля")


# Команда /list
# Equivalent to the main_list callback handler
@require_role("viewer")
async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    user_logger.log_user_action(user_id, "command_start", {"command": "/list"})
    _record_action(context, "/list:start")

    # ✅ ИСПРАВЛЕНИЕ: используем новый service для получения списка
    participants = participant_service.get_all_participants()

    if not participants:
        await update.message.reply_text(
            "📋 **Список участников пуст**\n\nИспользуйте /add для добавления участников.",
            parse_mode="Markdown",
        )
        user_logger.log_user_action(
            user_id, "command_end", {"command": "/list", "count": 0}
        )
        return

    # Формируем список участников
    message = f"📋 **Список участников ({len(participants)} чел.):**\n\n"
    user_logger.log_user_action(
        user_id, "command_end", {"command": "/list", "count": len(participants)}
    )

    for p in participants:
        role_emoji = "👤" if p.Role == "CANDIDATE" else "👨‍💼"
        department = f" ({p.Department})" if p.Role == "TEAM" and p.Department else ""

        message += f"{role_emoji} **{p.FullNameRU}**\n"
        message += f"   • Роль: {p.Role}{department}\n"
        message += f"   • ID: {p.id}\n\n"

    await _send_response_with_menu_button(update, message)


# Команда /export
# Equivalent to the main_export callback handler
@require_role("viewer")
async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_logger.log_user_action(
        user_id, "command_start", {"command": "/export", "params": context.args}
    )
    _record_action(context, "/export:start")
    role = get_user_role(user_id)
    logger.info("User %s requested export", user_id)

    await _send_response_with_menu_button(
        update,
        "📤 **Экспорт данных** (заглушка)\n\n"
        "🔧 Функция в разработке.\n"
        "Пример: /export worship team - экспорт участников worship команды",
    )
    user_logger.log_user_action(user_id, "command_end", {"command": "/export"})


# Команда /cancel
@require_role("viewer")
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    user_logger.log_user_action(user_id, "command_start", {"command": "/cancel"})
    _record_action(context, "/cancel:start")
    _log_session_end(context, user_id)
    if context.user_data:
        context.user_data.clear()
        logger.info("User %s cancelled the add flow.", user_id)
    else:
        logger.info("User %s cancelled a non-existent operation.", user_id)

    await _cleanup_messages(context, update.effective_chat.id)
    await _show_main_menu(update, context, is_return=True)
    user_logger.log_user_action(user_id, "command_end", {"command": "/cancel"})
    return ConversationHandler.END


async def cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle cancel buttons and return to the main menu."""
    query = update.callback_query
    user_id = update.effective_user.id
    user_logger.log_user_action(
        user_id, "command_start", {"command": "cancel_callback", "data": query.data}
    )
    _record_action(context, "cancel_callback:start")
    _log_session_end(context, user_id)

    logger.info(f"User {user_id} cancelled operation via {query.data}")

    await query.answer()

    await _cleanup_messages(context, update.effective_chat.id)
    cleanup_user_data_safe(context, update.effective_user.id)
    await _show_main_menu(update, context, is_return=True)
    user_logger.log_user_action(user_id, "command_end", {"command": "cancel_callback"})
    return ConversationHandler.END


# Обработка и подтверждение данных участника
async def process_participant_confirmation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    is_update: bool = False,
) -> int:
    """Обрабатывает ввод пользователя на этапе подтверждения."""

    # Копия текста подтверждения или его части может приходить обратно от пользователя
    is_block = "Имя (рус):" in text and "Пол:" in text
    if text.startswith("🔍") or "Вот что я понял" in text or is_block:
        parsed = parse_template_format(text)
    else:
        parsed = parse_participant_data(text, is_update=is_update)

    # Определяем, является ли это точечным исправлением или массовым обновлением
    existing = context.user_data.get("parsed_participant", {}) if is_update else {}

    if is_update:
        participant_data = merge_participant_data(existing, parsed)
    else:
        participant_data = parsed

    valid, error = validate_participant_data(participant_data)
    if not valid:
        logger.error("Parsing error: %s | Text: %s", error, text)
        await update.message.reply_text(f"❌ {error}")
        return COLLECTING_DATA

    existing_participant = None
    if not is_update:
        existing_participant = participant_service.check_duplicate(
            participant_data["FullNameRU"], user_id=user_id
        )

    if existing_participant:
        # Найден дубль - объединяем старые и новые данные
        merged_data = merge_participant_data(existing_participant, participant_data)
        context.user_data["parsed_participant"] = merged_data
        context.user_data["duplicate"] = True

        duplicate_warning = f"""
⚠️ **ВНИМАНИЕ: Участник уже существует!**

🆔 **Существующий участник (ID: {existing_participant.id}):**
👤 Имя: {existing_participant.FullNameRU}
⚥ Пол: {existing_participant.Gender}
👥 Роль: {existing_participant.Role}
⛪ Церковь: {existing_participant.Church}

🔄 **Новые данные:**
👤 Имя: {participant_data['FullNameRU']}
⚥ Пол: {participant_data['Gender']}
👥 Роль: {participant_data['Role']}
⛪ Церковь: {participant_data['Church']}

❓ **Что делать?**
- **ДА** - добавить как нового участника (возможен дубль)
- **НЕТ** - отменить добавление
- **ЗАМЕНИТЬ** - заменить существующего участника новыми данными

❌ /cancel для полной отмены
        """

        await update.message.reply_text(
            duplicate_warning,
            parse_mode="Markdown",
            reply_markup=get_duplicate_keyboard(),
        )
        return CONFIRMING_DUPLICATE

    if is_update:
        changes = detect_changes(existing, participant_data)
        if not changes:
            await update.message.reply_text(
                "Изменений не обнаружено. Выберите действие:",
                reply_markup=get_no_changes_keyboard(),
            )
            return CONFIRMING_DATA

        context.user_data["parsed_participant"] = participant_data
        context.user_data["duplicate"] = False
        confirmation_text = (
            "🔄 **Исправление данных:**\n\n"
            "✏️ **Изменено:**\n"
            + "\n".join(changes)
            + "\n\n👤 **Итоговые данные:**\n"
            + format_participant_block(participant_data)
            + "\n\n✅ **Что делать дальше?**\n"
            "- Напишите **ДА** или **НЕТ**\n"
            "- Или пришлите новые исправления"
            + "\n\n✏️ **Чтобы исправить поле, нажмите на кнопку ниже.**"
        )

        keyboard = get_edit_keyboard(participant_data)

        await update.message.reply_text(
            confirmation_text,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
        return CONFIRMING_DATA

    # Дублей нет - показываем обычное подтверждение
    context.user_data["parsed_participant"] = participant_data
    context.user_data["duplicate"] = False

    await show_confirmation(update, context, participant_data)
    return CONFIRMING_DATA


@require_role("coordinator")
@smart_cleanup_on_error
@log_state_transitions
async def handle_save_confirmation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handles the final confirmation via the 'Save' button."""
    query = update.callback_query
    user_id = update.effective_user.id

    logger.info(f"Save confirmation requested by user {user_id}")
    logger.debug(f"callback_data: {query.data}")
    logger.debug(f"user_data keys: {list(context.user_data.keys())}")

    await query.answer()
    await _cleanup_messages(context, update.effective_chat.id)

    participant_data = context.user_data.get("parsed_participant", {})
    if not participant_data:
        await query.message.reply_text(
            "❌ Не удалось найти данные для сохранения. Попробуйте снова."
        )
        cleanup_user_data_safe(context, update.effective_user.id)
        return ConversationHandler.END

    is_update = "participant_id" in context.user_data

    # Проверка на дубликат (только при создании нового)
    if not is_update:
        existing = participant_service.check_duplicate(
            participant_data.get("FullNameRU"), user_id=user_id
        )
        if existing:
            context.user_data["existing_participant_id"] = existing.get("id")
            message = "⚠️ **Найден дубликат!**\n\n"
            message += format_participant_block(existing)
            message += "\n\nЧто делаем?"
            await query.message.reply_text(
                message,
                parse_mode="Markdown",
                reply_markup=get_duplicate_keyboard(),
            )
            return CONFIRMING_DUPLICATE

    # Сохранение или обновление
    try:
        if is_update:
            participant_id = context.user_data["participant_id"]
            participant_service.update_participant(
                participant_id, participant_data, user_id=user_id
            )
            user_logger.log_participant_operation(
                user_id, "update", participant_data, participant_id
            )
            user_logger.log_user_action(
                user_id,
                "command_end",
                {
                    "command": "/add",
                    "participant_id": participant_id,
                    "result": "updated",
                },
            )
            success_message = f"✅ **Участник {participant_data['FullNameRU']} (ID: {participant_id}) успешно обновлен!**"
        else:
            new_participant = participant_service.add_participant(
                participant_data, user_id=user_id
            )
            user_logger.log_participant_operation(
                user_id, "add", participant_data, new_participant.id
            )
            user_logger.log_user_action(
                user_id,
                "command_end",
                {
                    "command": "/add",
                    "participant_id": new_participant.id,
                    "result": "added",
                },
            )
            success_message = f"✅ **Участник {new_participant.FullNameRU} (ID: {new_participant.id}) успешно добавлен!**"

        await query.message.reply_text(
            success_message,
            parse_mode="Markdown",
            reply_markup=get_post_action_keyboard(),
        )
    except (DatabaseError, BotException, ValidationError) as e:
        logger.error("Error during save confirmation: %s", e)
        await query.message.reply_text(f"❌ Произошла ошибка: {e}")

    cleanup_user_data_safe(context, update.effective_user.id)
    return ConversationHandler.END


# Обработка неизвестных команд и текстовых сообщений
@require_role("viewer")
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message_text = update.message.text.strip()
    logger.info("User %s sent message: %s", user_id, message_text)

    # Отладка состояния пользователя
    logger.info(f"User {user_id} state: {context.user_data}")

    # В будущем здесь будет NLP обработка
    await update.message.reply_text(
        f'🤖 Получено сообщение: "{message_text}"\n\n'
        "🔧 NLP обработка в разработке.\n"
        "Пока используйте команды: /help для справки.",
        parse_mode="Markdown",
    )


# Обработка подтверждения пользователя
@require_role("coordinator")
@smart_cleanup_on_error
@log_state_transitions
async def handle_participant_confirmation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Обрабатывает текстовый ввод на этапе подтверждения (только для исправлений)."""
    user_id = update.effective_user.id
    text = update.message.text.strip()

    logger.debug(
        "Confirmation handler context for user %s: %s", user_id, context.user_data
    )

    if clear_expired_edit(context):
        await update.message.reply_text(
            "⏳ Время редактирования истек. Выберите поле снова или нажмите /cancel."
        )
        return CONFIRMING_DATA

    field_to_edit = context.user_data.get("field_to_edit")
    clear_job = context.user_data.pop("clear_edit_job", None)
    if clear_job:
        clear_job.schedule_removal()

    if field_to_edit:
        participant_data = context.user_data.get("parsed_participant", {})
        logger.info(
            "User %s editing field %s with value: %s", user_id, field_to_edit, text
        )

        try:
            updated_data, changes = update_single_field(
                participant_data, field_to_edit, text
            )
        except ValidationError:
            field_label = FIELD_LABELS.get(field_to_edit, field_to_edit)
            error_text = MESSAGES["VALIDATION_ERRORS"].get(
                field_to_edit, f"Недопустимое значение для поля {field_label}"
            )
            await update.message.reply_text(
                f"❌ {error_text}\n\n🔄 Попробуйте еще раз или нажмите /cancel для отмены."
            )
            # НЕ очищаем field_to_edit - пользователь остается в режиме редактирования
            return CONFIRMING_DATA

        context.user_data["parsed_participant"] = updated_data
        context.user_data.pop("field_to_edit", None)

        logger.info("Changes after edit: %s", "; ".join(changes) or "no changes")

        await show_confirmation(update, context, updated_data)
        return CONFIRMING_DATA

    logger.warning(
        "field_to_edit missing in context for user %s during confirmation", user_id
    )

    # Теперь эта функция обрабатывает только исправления, отправляя их в process_participant_confirmation
    # Логика ДА/НЕТ полностью удалена и заменена кнопкой
    await process_participant_confirmation(update, context, text, is_update=True)
    return CONFIRMING_DATA


@smart_cleanup_on_error
async def edit_field_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Обрабатывает нажатие на кнопку редактирования поля."""
    query = update.callback_query
    await query.answer()

    _add_message_to_cleanup(context, query.message.message_id)

    field_to_edit = query.data.split("_")[1]
    user_id = update.effective_user.id
    logger.info("User %s selected field %s for editing", user_id, field_to_edit)

    # Save field in context and start timeout job
    context.user_data["field_to_edit"] = field_to_edit

    if job := context.user_data.get("clear_edit_job"):
        job.schedule_removal()

    timeout_job = safe_create_timeout_job(
        context, clear_field_to_edit, FIELD_EDIT_TIMEOUT, user_id
    )
    if timeout_job:
        context.user_data["clear_edit_job"] = timeout_job

    keyboard_map = {
        "Gender": get_gender_selection_keyboard_simple,
        "Role": get_role_selection_keyboard,
        "Size": get_size_selection_keyboard,
        "Department": get_department_selection_keyboard,
    }

    cancel_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton("↩️ Назад", callback_data="field_edit_cancel")]]
    )

    if field_to_edit in keyboard_map:
        kb = keyboard_map[field_to_edit]()
        msg = await query.message.reply_text("Выберите значение:", reply_markup=kb)
    else:
        msg = await query.message.reply_text(
            f"Пришлите новое значение для поля **{FIELD_LABELS.get(field_to_edit, field_to_edit)}**",
            parse_mode="Markdown",
            reply_markup=cancel_markup,
        )
    _add_message_to_cleanup(context, msg.message_id)

    return CONFIRMING_DATA


@smart_cleanup_on_error
@log_state_transitions
async def handle_enum_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Обрабатывает выбор значения из enum-клавиатуры или переход к ручному вводу."""
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = update.effective_user.id
    current_state = context.user_data.get("current_state", CONFIRMING_DATA)
    filling_context = context.user_data.get("filling_missing_field", False)

    match = re.match(r"^(gender|role|size|dept)_(.+)$", data)
    if not match:
        return current_state

    prefix, value = match.groups()
    field_map = {
        "gender": "Gender",
        "role": "Role",
        "size": "Size",
        "dept": "Department",
    }
    field = field_map[prefix]

    if filling_context or current_state in (COLLECTING_DATA, FILLING_MISSING_FIELDS):
        participant_data = context.user_data.get("add_flow_data", {})
        before_role = participant_data.get("Role")
        participant_data, _ = update_single_field(participant_data, field, value)
        if field == "Role" and value:
            if value == "TEAM" or before_role == "TEAM":
                participant_data["Department"] = ""
        context.user_data["add_flow_data"] = participant_data
        next_field = get_next_missing_field(participant_data)
        if next_field is None:
            context.user_data["parsed_participant"] = participant_data
            await show_confirmation(update, context, participant_data)
            context.user_data["current_state"] = CONFIRMING_DATA
            context.user_data["filling_missing_field"] = False
            return CONFIRMING_DATA
        await show_interactive_missing_field(update, context, participant_data)
        context.user_data["current_state"] = FILLING_MISSING_FIELDS
        return FILLING_MISSING_FIELDS

    participant_data = context.user_data.get("parsed_participant", {})
    before_role = participant_data.get("Role")
    updated_data, _changes = update_single_field(participant_data, field, value)
    if field == "Role" and value:
        if value == "TEAM" or before_role == "TEAM":
            updated_data["Department"] = ""
    context.user_data["parsed_participant"] = updated_data
    context.user_data.pop("field_to_edit", None)

    if job := context.user_data.pop("clear_edit_job", None):
        job.schedule_removal()

    await show_confirmation(update, context, updated_data)
    return CONFIRMING_DATA


@smart_cleanup_on_error
async def handle_continue_editing_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Shows the edit keyboard again when user chooses to continue editing."""
    query = update.callback_query
    await query.answer()

    participant_data = context.user_data.get("parsed_participant", {})
    keyboard = get_edit_keyboard(participant_data)

    msg = await query.message.reply_text(
        "\u270f\ufe0f Выберите поле для редактирования или сохраните без изменений.",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )
    _add_message_to_cleanup(context, msg.message_id)

    return CONFIRMING_DATA


@smart_cleanup_on_error
async def handle_field_edit_cancel(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Возвращает пользователя к подтверждению данных без сброса всего диалога."""
    query = update.callback_query
    user_id = update.effective_user.id

    logger.info(f"User {user_id} cancelled field editing")
    await query.answer()

    context.user_data.pop("field_to_edit", None)
    context.user_data.pop("edit_timeout", None)

    if job := context.user_data.pop("clear_edit_job", None):
        job.schedule_removal()

    participant_data = context.user_data.get("parsed_participant", {})
    if participant_data:
        await show_confirmation(update, context, participant_data)
        await query.edit_message_text(
            "Редактирование отменено. Выберите другое поле для изменения или сохраните данные.",
            reply_markup=get_edit_keyboard(participant_data),
        )
        return CONFIRMING_DATA

    await query.message.reply_text("Данные участника не найдены. Начните заново с /add")
    cleanup_user_data_safe(context, user_id)
    return ConversationHandler.END


@smart_cleanup_on_error
async def handle_recover_confirmation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Return to the confirmation step after recovery."""
    query = update.callback_query
    await query.answer()
    participant_data = context.user_data.get("parsed_participant")
    if participant_data:
        await show_confirmation(update, context, participant_data)
        return CONFIRMING_DATA
    await query.message.reply_text("Данные участника не найдены. Начните заново с /add")
    return ConversationHandler.END


@smart_cleanup_on_error
async def handle_recover_input(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Resume input of missing fields after recovery."""
    query = update.callback_query
    await query.answer()
    participant_data = context.user_data.get("add_flow_data")
    if participant_data:
        await show_interactive_missing_field(update, context, participant_data)
        return FILLING_MISSING_FIELDS
    await query.message.reply_text("Данные не найдены. Начните заново с /add")
    return ConversationHandler.END


@smart_cleanup_on_error
@log_state_transitions
async def handle_duplicate_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handles duplicate confirmation buttons."""
    query = update.callback_query
    await query.answer()

    action = query.data
    participant_data = context.user_data.get("parsed_participant", {})
    user_id = update.effective_user.id if update.effective_user else 0

    if action == "dup_add_new":
        try:
            new_participant = participant_service.add_participant(
                participant_data, user_id=user_id
            )
            user_logger.log_participant_operation(
                user_id, "add", participant_data, new_participant.id
            )
            user_logger.log_user_action(
                user_id,
                "command_end",
                {
                    "command": "/add",
                    "participant_id": new_participant.id,
                    "result": "added_duplicate",
                },
            )
        except ValidationError as e:
            await query.message.reply_text(f"❌ Ошибка валидации: {e}")
            return ConversationHandler.END
        except ParticipantNotFoundError as e:  # unlikely here
            await query.message.reply_text(str(e))
            return ConversationHandler.END
        except (DatabaseError, BotException) as e:
            logger.error("Error adding participant: %s", e)
            await query.message.reply_text(
                "❌ Ошибка базы данных при добавлении участника."
            )
            return ConversationHandler.END
        cleanup_user_data_safe(context, update.effective_user.id)

        await query.message.reply_text(
            f"✅ **Участник добавлен как новый (возможен дубль)**\n\n"
            f"🆔 ID: {new_participant.id}\n"
            f"👤 Имя: {participant_data['FullNameRU']}\n\n"
            f"⚠️ Обратите внимание на возможное дублирование!",
            parse_mode="Markdown",
            reply_markup=get_post_action_keyboard(),
        )

    elif action == "dup_replace":
        existing = participant_service.check_duplicate(
            participant_data["FullNameRU"], user_id=user_id
        )
        if existing:
            try:
                updated = participant_service.update_participant(
                    existing.id, participant_data, user_id=user_id
                )
                user_logger.log_participant_operation(
                    user_id, "update", participant_data, existing.id
                )
                user_logger.log_user_action(
                    user_id,
                    "command_end",
                    {
                        "command": "/add",
                        "participant_id": existing.id,
                        "result": "updated_duplicate",
                    },
                )
            except ValidationError as e:
                await query.message.reply_text(f"❌ Ошибка валидации: {e}")
                return ConversationHandler.END
            except ParticipantNotFoundError as e:
                await query.message.reply_text(str(e))
                return ConversationHandler.END
            except (DatabaseError, BotException) as e:
                logger.error("Error updating participant: %s", e)
                await query.message.reply_text(
                    "❌ Ошибка базы данных при обновлении участника."
                )
                return ConversationHandler.END
            cleanup_user_data_safe(context, update.effective_user.id)

            if updated:
                await query.message.reply_text(
                    f"🔄 **Участник обновлен!**\n\n"
                    f"🆔 ID: {existing.id}\n"
                    f"👤 Имя: {participant_data['FullNameRU']}\n"
                    f"👥 Роль: {participant_data['Role']}\n\n"
                    f"📋 Данные заменены новыми значениями",
                    parse_mode="Markdown",
                    reply_markup=get_post_action_keyboard(),
                )
            else:
                await query.message.reply_text("❌ Ошибка обновления участника.")
        else:
            await query.message.reply_text("❌ Существующий участник не найден.")

    return ConversationHandler.END


# Обработка ошибок
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    error_type = type(context.error).__name__
    ERROR_STATS[error_type] += 1

    # Special handling for Airtable errors
    if AIRTABLE_AVAILABLE and isinstance(context.error, AirtableApiError):
        logging.getLogger("errors").error(
            "Airtable API error for update %s: %s | count=%s",
            update,
            context.error,
            ERROR_STATS[error_type],
            exc_info=context.error,
        )
    else:
        logging.getLogger("errors").error(
            "Bot error for update %s: %s | count=%s",
            update,
            context.error,
            ERROR_STATS[error_type],
            exc_info=context.error,
        )


# Factory for participant repositories
def create_participant_repository():
    """Factory function to create the appropriate participant repository."""
    if config.DATABASE_TYPE == "airtable":
        logger.info("Using Airtable as database backend")
        return AirtableParticipantRepository()
    else:
        logger.info("Using SQLite as database backend")
        return SqliteParticipantRepository()


# Основная функция
def main():
    # Проверка конфигурации при старте
    if config.DATABASE_TYPE == "airtable":
        if not config.AIRTABLE_TOKEN or not config.AIRTABLE_BASE_ID:
            print("❌ ERROR: Airtable configuration incomplete!")
            print("   Set AIRTABLE_TOKEN and AIRTABLE_BASE_ID in .env file")
            return

        # Test Airtable connection
        try:
            from repositories.airtable_client import AirtableClient

            client = AirtableClient()
            if not client.test_connection():
                print("❌ ERROR: Cannot connect to Airtable!")
                return
            print("✅ Airtable connection successful")
        except Exception as e:
            print(f"❌ ERROR: Airtable connection failed: {e}")
            return

    # Инициализируем базу данных только для SQLite
    if config.DATABASE_TYPE != "airtable":
        init_database()

    # Загружаем справочники в кэш
    load_reference_data()

    # Initialize repository and service instances
    global participant_repository, participant_service
    participant_repository = create_participant_repository()
    participant_service = ParticipantService(repository=participant_repository)

    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Middleware to log all incoming updates
    application.add_handler(MessageHandler(filters.ALL, log_all_updates), group=-1)

    search_conv = ConversationHandler(
        entry_points=[
            CommandHandler("search", search_command),
            CallbackQueryHandler(handle_search_callback, pattern="^main_search$"),
        ],
        states={
            SEARCHING_PARTICIPANTS: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, handle_search_input
                )
            ],
            SELECTING_PARTICIPANT: [
                CallbackQueryHandler(
                    handle_participant_selection, pattern="^select_participant_"
                )
            ],
            CHOOSING_ACTION: [
                CallbackQueryHandler(handle_action_selection, pattern="^action_"),
                CallbackQueryHandler(handle_action_selection, pattern="^search_new$"),
            ],
            EXECUTING_ACTION: [
                CallbackQueryHandler(
                    handle_action_selection, pattern="^confirm_delete_"
                ),
                CallbackQueryHandler(handle_action_selection, pattern="^action_cancel$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_command),
            CallbackQueryHandler(cancel_callback, pattern="^main_cancel$"),
            CallbackQueryHandler(handle_main_menu_callback, pattern="^main_menu$"),
        ],
    )

    add_conv = ConversationHandler(
        entry_points=[
            CommandHandler("add", add_command),
            CallbackQueryHandler(handle_add_callback, pattern="^main_add$"),
        ],
        states={
            COLLECTING_DATA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_partial_data)
            ],
            FILLING_MISSING_FIELDS: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, handle_missing_field_input
                ),
                CallbackQueryHandler(
                    handle_enum_selection, pattern="^(gender|role|size|dept)_.+$"
                ),
            ],
            CONFIRMING_DATA: [
                CallbackQueryHandler(
                    handle_save_confirmation, pattern="^confirm_save$"
                ),
                CallbackQueryHandler(
                    handle_enum_selection,
                    pattern="^(gender|role|size|dept)_.+$",
                ),
                CallbackQueryHandler(
                    handle_field_edit_cancel, pattern="^field_edit_cancel$"
                ),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, handle_participant_confirmation
                ),
                CallbackQueryHandler(edit_field_callback, pattern="^edit_"),
                CallbackQueryHandler(
                    handle_continue_editing_callback, pattern="^continue_editing$"
                ),
            ],
            CONFIRMING_DUPLICATE: [
                CallbackQueryHandler(handle_duplicate_callback, pattern="^dup_"),
            ],
            RECOVERING: [
                CallbackQueryHandler(
                    handle_recover_confirmation, pattern="^recover_confirmation$"
                ),
                CallbackQueryHandler(handle_recover_input, pattern="^recover_input$"),
                CallbackQueryHandler(handle_add_callback, pattern="^main_add$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_command),
            CallbackQueryHandler(cancel_callback, pattern="^main_cancel$"),
        ],
    )
    # ConversationHandler должен быть зарегистрирован первым
    application.add_handler(search_conv)
    application.add_handler(add_conv)

    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(
        CallbackQueryHandler(
            handle_main_menu_callback, pattern="^main_(list|export|help|menu|cancel)$"
        )
    )
    application.add_handler(CommandHandler("edit", edit_command))
    application.add_handler(CommandHandler("edit_field", edit_field_command))
    application.add_handler(CommandHandler("delete", delete_command))
    application.add_handler(CommandHandler("list", list_command))
    application.add_handler(CommandHandler("export", export_command))
    application.add_handler(CommandHandler("cancel", cancel_command))

    # Обработчик текстовых сообщений
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # Обработчик ошибок
    application.add_error_handler(error_handler)

    database_type = config.DATABASE_TYPE.upper()
    print(f"🤖 Бот @{BOT_USERNAME} запущен!")
    print(f"🗄️ Database: {database_type}")
    print("🔄 Polling started...")

    # Запускаем бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
