import time
from datetime import datetime

from telegram.ext import ContextTypes

from .user_logger import UserActionLogger

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
