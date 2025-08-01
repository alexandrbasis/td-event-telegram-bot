import logging
from logging.handlers import RotatingFileHandler
import re
from typing import List, Dict, Optional
from dataclasses import asdict
import time
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
from config import BOT_TOKEN, BOT_USERNAME, COORDINATOR_IDS, VIEWER_IDS
from utils.decorators import require_role
from utils.cache import load_reference_data
from utils.timeouts import set_edit_timeout, clear_expired_edit
from database import init_database
from repositories.participant_repository import SqliteParticipantRepository
from services.participant_service import ParticipantService
from parsers.participant_parser import (
    parse_participant_data,
    is_template_format,
    parse_template_format,
    parse_unstructured_text,
)
from services.participant_service import (
    merge_participant_data,
    format_participant_block,
    detect_changes,
    update_single_field,
    get_edit_keyboard,
    FIELD_LABELS,
    get_gender_selection_keyboard,
    get_role_selection_keyboard,
    get_size_selection_keyboard,
    get_department_selection_keyboard,
)
from utils.validators import validate_participant_data
from utils.exceptions import (
    BotException,
    ParticipantNotFoundError,
    ValidationError,
    DatabaseError,
)
from messages import MESSAGES
from states import CONFIRMING_DATA, CONFIRMING_DUPLICATE, COLLECTING_DATA


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

        try:
            return await func(update, context, *args, **kwargs)

        except ValidationError as e:
            # Ошибки валидации - остаёмся в текущем состоянии
            logger.warning(
                f"Validation error for user {user_id} in {func.__name__}: {e}"
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
            logger.warning(
                f"Participant not found for user {user_id} in {func.__name__}: {e}"
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
                logger.error(f"JobQueue error for user {user_id}: {e}")
                try:
                    if update.message:
                        await update.message.reply_text(
                            "⚠️ Техническая проблема с таймерами. Продолжайте редактирование.\n"
                            "Введите новое значение или нажмите /cancel для отмены."
                        )
                    elif update.callback_query:
                        await update.callback_query.answer()
                        await update.callback_query.message.reply_text(
                            "⚠️ Техническая проблема с таймерами. Продолжайте редактирование.\n"
                            "Введите новое значение или нажмите /cancel для отмены."
                        )
                except Exception as send_error:
                    logger.error(
                        f"Failed to send timer error message to user {user_id}: {send_error}"
                    )
                participant_data = context.user_data.get("parsed_participant")
                if participant_data:
                    await show_confirmation(update, context, participant_data)
                return context.user_data.get("current_state", CONFIRMING_DATA)
            else:
                raise

        except (DatabaseError, BotException) as e:
            # Серьёзные ошибки - очищаем состояние
            logger.error(
                f"Critical error for user {user_id} in {func.__name__}: {type(e).__name__}: {e}"
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
                logger.error(
                    f"Failed to send critical error message to user {user_id}: {send_error}"
                )

            return ConversationHandler.END

        except Exception as e:
            # Неизвестные ошибки - очищаем состояние для безопасности
            logger.error(
                f"Unexpected error for user {user_id} in {func.__name__}: {type(e).__name__}: {e}",
                exc_info=True,
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
                logger.error(
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


# --- Конец вспомогательных функций ---


# Настройка логирования
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
handler = RotatingFileHandler("bot.log", maxBytes=10 * 1024 * 1024, backupCount=5)
handler.setFormatter(logging.Formatter(LOG_FORMAT))

# Отдельный лог для SQL-запросов
sql_handler = RotatingFileHandler("sql.log", maxBytes=10 * 1024 * 1024, backupCount=5)
sql_handler.setFormatter(logging.Formatter(LOG_FORMAT))
sql_logger = logging.getLogger("sql")
sql_logger.addHandler(sql_handler)


def setup_logging():
    """Configure logging levels for production."""
    logging.basicConfig(level=logging.INFO, handlers=[handler], format=LOG_FORMAT)
    # logging.getLogger(__name__).setLevel(logging.DEBUG)
    sql_logger.setLevel(logging.WARNING)


setup_logging()

logger = logging.getLogger(__name__)

# Timeout in seconds to wait for user input when editing a specific field
FIELD_EDIT_TIMEOUT = 300

# Initialize repository and service instances
participant_repository = SqliteParticipantRepository()
participant_service = ParticipantService(repository=participant_repository)

# --- REQUIRED AND OPTIONAL FIELDS ---
REQUIRED_FIELDS = ["FullNameRU", "Gender", "Size", "Church", "Role"]
OPTIONAL_FIELDS = [
    "FullNameEN",
    "CountryAndCity",
    "SubmittedBy",
    "ContactInformation",
    "Department",
]


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

    keyboard: list[list[InlineKeyboardButton]]
    if user_id in COORDINATOR_IDS:
        keyboard = [
            [
                InlineKeyboardButton("➕ Добавить", callback_data="main_add"),
                InlineKeyboardButton("📋 Список", callback_data="main_list"),
            ],
            [
                InlineKeyboardButton("📤 Экспорт", callback_data="main_export"),
                InlineKeyboardButton("ℹ️ Помощь", callback_data="main_help"),
            ],
        ]
    else:
        keyboard = [
            [
                InlineKeyboardButton("📋 Список", callback_data="main_list"),
                InlineKeyboardButton("📤 Экспорт", callback_data="main_export"),
            ],
            [InlineKeyboardButton("ℹ️ Помощь", callback_data="main_help")],
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)

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
    logger.info("User %s started /start", update.effective_user.id)
    await _cleanup_messages(context, update.effective_chat.id)
    await _show_main_menu(update, context)


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
    return COLLECTING_DATA


@require_role("viewer")
async def handle_main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатия на кнопки главного меню."""
    query = update.callback_query
    await query.answer()
    data = query.data

    await query.edit_message_reply_markup(reply_markup=None)

    if data == "main_cancel":
        await _cleanup_messages(context, update.effective_chat.id)
        cleanup_user_data_safe(context, update.effective_user.id)
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


# Equivalent to the main_help callback handler
# Команда /help
@require_role("viewer")
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
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


# Команда /add
@require_role("coordinator")
@cleanup_on_error
async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the /add flow and initializes the session."""
    user_id = update.effective_user.id
    logger.info("User %s started add participant", user_id)

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
    return COLLECTING_DATA


@require_role("coordinator")
@smart_cleanup_on_error
async def handle_partial_data(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Collects and processes partial data, supporting multiple formats."""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    _add_message_to_cleanup(context, update.message.message_id)
    participant_data = context.user_data.get("add_flow_data", {})

    # 1. Check if user pasted a full template (highest priority)
    if is_template_format(text):
        parsed_update = parse_template_format(text)
        for key, value in parsed_update.items():
            if value:
                participant_data[key] = value
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

            for key, value in parsed_chunk.items():
                if value:
                    participant_data[key] = value

    # --- NAME DUPLICATE CHECK BLOCK ---
    newly_identified_name = participant_data.get("FullNameRU")
    if newly_identified_name and not context.user_data.get("participant_id"):
        existing_participant = participant_service.check_duplicate(
            newly_identified_name
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
        status_message = format_status_message(participant_data)
        cancel_markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton("❌ Отмена", callback_data="main_cancel")]]
        )
        msg = await update.message.reply_text(
            status_message, parse_mode="Markdown", reply_markup=cancel_markup
        )
        _add_message_to_cleanup(context, msg.message_id)
        context.user_data["current_state"] = COLLECTING_DATA
        return COLLECTING_DATA


# Команда /edit
@require_role("coordinator")
async def edit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    logger.info("User %s started edit participant", user_id)

    await _send_response_with_menu_button(
        update,
        "✏️ **Редактирование участника** (заглушка)\n\n"
        "🔧 Функция в разработке.\n"
        "Пример: /edit 123 - редактировать участника с ID 123",
    )


# Команда /delete
@require_role("coordinator")
async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    role = get_user_role(user_id)
    logger.info("User %s started delete participant", user_id)

    await _send_response_with_menu_button(
        update,
        "🗑️ **Удаление участника** (заглушка)\n\n"
        "🔧 Функция в разработке.\n"
        "Пример: /delete 123 - удалить участника с ID 123",
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
            participant_id, **kwargs
        )

        if success:
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
    logger.info("User %s requested participants list", user_id)

    # ✅ ИСПРАВЛЕНИЕ: используем новый service для получения списка
    participants = participant_service.get_all_participants()

    if not participants:
        await update.message.reply_text(
            "📋 **Список участников пуст**\n\nИспользуйте /add для добавления участников.",
            parse_mode="Markdown",
        )
        return

    # Формируем список участников
    message = f"📋 **Список участников ({len(participants)} чел.):**\n\n"

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
    role = get_user_role(user_id)
    logger.info("User %s requested export", user_id)

    await _send_response_with_menu_button(
        update,
        "📤 **Экспорт данных** (заглушка)\n\n"
        "🔧 Функция в разработке.\n"
        "Пример: /export worship team - экспорт участников worship команды",
    )


# Команда /cancel
@require_role("viewer")
async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    if context.user_data:
        context.user_data.clear()
        logger.info("User %s cancelled the add flow.", user_id)
    else:
        logger.info("User %s cancelled a non-existent operation.", user_id)

    await _cleanup_messages(context, update.effective_chat.id)
    await _show_main_menu(update, context, is_return=True)
    return ConversationHandler.END


async def cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle cancel buttons and return to the main menu."""
    query = update.callback_query
    user_id = update.effective_user.id

    logger.info(f"User {user_id} cancelled operation via {query.data}")

    await query.answer()

    await _cleanup_messages(context, update.effective_chat.id)
    cleanup_user_data_safe(context, update.effective_user.id)
    await _show_main_menu(update, context, is_return=True)
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
            participant_data["FullNameRU"]
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
            participant_data.get("FullNameRU")
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
            participant_service.update_participant(participant_id, participant_data)
            logger.info(
                f"✅ User {user_id} successfully updated participant {participant_id}"
            )
            success_message = f"✅ **Участник {participant_data['FullNameRU']} (ID: {participant_id}) успешно обновлен!**"
        else:
            new_participant = participant_service.add_participant(participant_data)
            logger.info(
                f"✅ User {user_id} successfully added participant {new_participant.id}: {new_participant.FullNameRU}"
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
            error_text = MESSAGES["VALIDATION_ERRORS"].get(
                field_to_edit, f"Недопустимое значение для поля {field_to_edit}"
            )
            await update.message.reply_text(f"❌ {error_text}")

            if context.job_queue:
                timeout_job = context.job_queue.run_once(
                    clear_field_to_edit, FIELD_EDIT_TIMEOUT, data=user_id
                )
                context.user_data["clear_edit_job"] = timeout_job
            else:
                logger.warning(
                    "JobQueue not available for user %s, skipping timeout job",
                    user_id,
                )
                set_edit_timeout(context, user_id, FIELD_EDIT_TIMEOUT)
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

    if context.job_queue:
        timeout_job = context.job_queue.run_once(
            clear_field_to_edit, FIELD_EDIT_TIMEOUT, data=user_id
        )
        context.user_data["clear_edit_job"] = timeout_job
    else:
        logger.warning(
            f"JobQueue not available for user {user_id}, skipping timeout job"
        )
        set_edit_timeout(context, user_id, FIELD_EDIT_TIMEOUT)

    keyboard_map = {
        "Gender": get_gender_selection_keyboard,
        "Role": get_role_selection_keyboard,
        "Size": get_size_selection_keyboard,
        "Department": get_department_selection_keyboard,
    }

    if field_to_edit in keyboard_map:
        kb = keyboard_map[field_to_edit]()
        msg = await query.message.reply_text("Выберите значение:", reply_markup=kb)
    else:
        msg = await query.message.reply_text(
            f"Пришлите новое значение для поля **{field_to_edit}**",
            parse_mode="Markdown",
        )
    _add_message_to_cleanup(context, msg.message_id)

    return CONFIRMING_DATA


@smart_cleanup_on_error
async def handle_enum_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Обрабатывает выбор значения из enum-клавиатуры или переход к ручному вводу."""
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = update.effective_user.id

    if data.startswith("manual_input_"):
        field = data.split("_", 1)[1]
        context.user_data["field_to_edit"] = field

        if job := context.user_data.get("clear_edit_job"):
            job.schedule_removal()
        if context.job_queue:
            timeout_job = context.job_queue.run_once(
                clear_field_to_edit, FIELD_EDIT_TIMEOUT, data=user_id
            )
            context.user_data["clear_edit_job"] = timeout_job
        else:
            logger.warning(
                f"JobQueue not available for user {user_id}, skipping timeout job"
            )
            set_edit_timeout(context, user_id, FIELD_EDIT_TIMEOUT)

        msg = await query.message.reply_text(
            f"Пришлите новое значение для поля **{field}**",
            parse_mode="Markdown",
        )
        _add_message_to_cleanup(context, msg.message_id)
        return CONFIRMING_DATA

    match = re.match(r"^(gender|role|size|dept)_(.+)$", data)
    if not match:
        return CONFIRMING_DATA

    prefix, value = match.groups()
    field_map = {
        "gender": "Gender",
        "role": "Role",
        "size": "Size",
        "dept": "Department",
    }
    field = field_map[prefix]

    participant_data = context.user_data.get("parsed_participant", {})
    updated_data, _changes = update_single_field(participant_data, field, value)
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
async def handle_duplicate_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handles duplicate confirmation buttons."""
    query = update.callback_query
    await query.answer()

    action = query.data
    participant_data = context.user_data.get("parsed_participant", {})

    if action == "dup_add_new":
        try:
            new_participant = participant_service.add_participant(participant_data)
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
        existing = participant_service.check_duplicate(participant_data["FullNameRU"])
        if existing:
            try:
                updated = participant_service.update_participant(
                    existing.id, participant_data
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
    logger.error(
        f"Bot error for update {update}: {context.error}", exc_info=context.error
    )


# Основная функция
def main():
    # Инициализируем базу данных
    init_database()

    # Загружаем справочники в кэш
    load_reference_data()

    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()

    add_conv = ConversationHandler(
        entry_points=[
            CommandHandler("add", add_command),
            CallbackQueryHandler(handle_add_callback, pattern="^main_add$"),
        ],
        states={
            COLLECTING_DATA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_partial_data)
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
                    handle_enum_selection,
                    pattern="^manual_input_.+$",
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
        },
        fallbacks=[
            CommandHandler("cancel", cancel_command),
            CallbackQueryHandler(cancel_callback, pattern="^main_cancel$"),
        ],
    )
    # ConversationHandler должен быть зарегистрирован первым
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

    print(f"🤖 Бот @{BOT_USERNAME} запущен!")
    print("🔄 Polling started...")

    # Запускаем бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
