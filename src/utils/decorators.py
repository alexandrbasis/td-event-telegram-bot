from functools import wraps
from config import COORDINATOR_IDS, VIEWER_IDS


def require_role(required_role):
    """Decorator to check user role for a command."""

    def decorator(func):
        @wraps(func)
        async def wrapper(update, context):
            user_id = update.effective_user.id

            if required_role == "coordinator" and user_id not in COORDINATOR_IDS:
                await update.message.reply_text(
                    "❌ Только координаторы могут выполнять эту команду."
                )
                return
            elif required_role == "viewer" and user_id not in (
                COORDINATOR_IDS + VIEWER_IDS
            ):
                await update.message.reply_text("❌ У вас нет доступа к этому боту.")
                return

            return await func(update, context)

        return wrapper

    return decorator
