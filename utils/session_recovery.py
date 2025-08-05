import logging
import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


def detect_interrupted_session(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """Определяет, была ли прервана сессия пользователя."""
    session_start = context.user_data.get("session_start")
    if session_start:
        age_minutes = (time.time() - session_start.timestamp()) / 60
        if age_minutes > 30:
            return False

    message_text = getattr(update.message, "text", "")
    excluded_commands = ["/help", "/list", "/export"]
    if any(message_text.startswith(cmd) for cmd in excluded_commands):
        return False

    has_partial_data = bool(
        context.user_data.get("add_flow_data")
        or context.user_data.get("parsed_participant")
        or context.user_data.get("field_to_edit")
    )
    is_command = message_text.startswith("/")
    return has_partial_data and is_command


async def handle_session_recovery(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Предлагает пользователю восстановить прерванную сессию."""
    user_id = update.effective_user.id if update.effective_user else None

    from utils.user_logger import UserActionLogger

    user_logger = UserActionLogger()
    user_logger.log_user_action(
        user_id,
        "session_recovery_offered",
        {
            "has_add_flow": bool(context.user_data.get("add_flow_data")),
            "has_parsed_participant": bool(
                context.user_data.get("parsed_participant")
            ),
            "has_field_edit": bool(context.user_data.get("field_to_edit")),
        },
    )

    recovery_options = []

    if context.user_data.get("parsed_participant"):
        recovery_options.append(
            [
                InlineKeyboardButton(
                    "📝 Продолжить редактирование", callback_data="recover_editing"
                )
            ]
        )

    if context.user_data.get("add_flow_data"):
        recovery_options.append(
            [
                InlineKeyboardButton(
                    "➕ Продолжить добавление", callback_data="recover_adding"
                )
            ]
        )

    recovery_options.extend(
        [
            [
                InlineKeyboardButton(
                    "🗑️ Очистить и начать заново", callback_data="clear_session"
                )
            ],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")],
        ]
    )

    keyboard = InlineKeyboardMarkup(recovery_options)

    await update.message.reply_text(
        "⏸️ **Обнаружена незавершенная операция**\n\n"
        "Похоже, вы не завершили предыдущее действие. Что делать?",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )
