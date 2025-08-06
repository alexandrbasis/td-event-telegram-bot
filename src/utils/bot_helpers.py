import logging
import time
from datetime import datetime
from functools import wraps

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from .user_logger import UserActionLogger

logger = logging.getLogger(__name__)
user_logger = UserActionLogger()


def _record_action(context: ContextTypes.DEFAULT_TYPE, action: str) -> None:
    """Append an action with timestamp to the user's history."""
    history = context.user_data.setdefault("action_history", [])
    history.append({"action": action, "timestamp": time.time()})
    if len(history) > 5:
        context.user_data["action_history"] = history[-5:]


def _log_session_end(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    """Log session duration using UserActionLogger."""
    start = context.user_data.pop("session_start", None)
    if start:
        duration = (datetime.utcnow() - start).total_seconds()
        user_logger.log_user_action(user_id, "session_end", {"duration": duration})


def cleanup_user_data_safe(
    context: ContextTypes.DEFAULT_TYPE, user_id: int | None = None
) -> None:
    """Safely clear user_data with logging."""
    if context.user_data:
        keys_to_clear = list(context.user_data.keys())
        context.user_data.clear()
        logger.info(
            "Cleared user_data for user %s: %s", user_id or "unknown", keys_to_clear
        )


def cleanup_on_error(func):
    """Decorator to automatically cleanup user_data on errors."""

    @wraps(func)
    async def wrapper(
        update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
    ):
        try:
            return await func(update, context, *args, **kwargs)
        except Exception as e:  # pragma: no cover - log path
            user_id = update.effective_user.id if update.effective_user else "unknown"
            logger.error(
                "Error in %s for user %s: %s", func.__name__, user_id, e, exc_info=True
            )
            cleanup_user_data_safe(context, update.effective_user.id)
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
            except Exception as send_error:  # pragma: no cover
                logger.error(
                    "Failed to send error message to user %s: %s", user_id, send_error
                )
            return ConversationHandler.END

    return wrapper
