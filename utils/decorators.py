from functools import wraps
from config import COORDINATOR_IDS, VIEWER_IDS


def require_role(required_role):
    """Decorator to check user role for a command or callback.

    For callback-only handlers where update.message is None, the decorator will
    respond via update.callback_query.message and call answer() to acknowledge
    the callback.
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(update, context):
            user_id = getattr(getattr(update, "effective_user", None), "id", None)

            unauthorized_message = None
            if required_role == "coordinator":
                if user_id not in COORDINATOR_IDS:
                    unauthorized_message = "❌ Только координаторы могут выполнять эту команду."
            elif required_role == "viewer":
                if user_id not in (COORDINATOR_IDS + VIEWER_IDS):
                    unauthorized_message = "❌ У вас нет доступа к этому боту."

            if unauthorized_message:
                # Prefer replying via callback when present
                callback_query = getattr(update, "callback_query", None)
                if callback_query is not None:
                    try:
                        # Acknowledge the callback to avoid Telegram client spinners
                        await callback_query.answer()
                    except Exception:
                        # Ignore acknowledgment errors
                        pass
                    if getattr(callback_query, "message", None) is not None:
                        await callback_query.message.reply_text(unauthorized_message)
                elif getattr(update, "message", None) is not None:
                    await update.message.reply_text(unauthorized_message)
                return

            return await func(update, context)

        return wrapper

    return decorator
