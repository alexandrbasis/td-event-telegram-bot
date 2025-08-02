import logging
import json
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, Optional


class UserActionLogger:
    """Structured logger for user-related actions."""

    USER_ACTION_LEVEL = logging.INFO + 5
    BUSINESS_LOGIC_LEVEL = logging.INFO + 7

    logging.addLevelName(USER_ACTION_LEVEL, "USER_ACTION")
    logging.addLevelName(BUSINESS_LOGIC_LEVEL, "BUSINESS_LOGIC")

    def __init__(self) -> None:
        self.logger = logging.getLogger("user_action")
        if not self.logger.handlers:
            handler = RotatingFileHandler(
                "user_actions.log", maxBytes=5 * 1024 * 1024, backupCount=5
            )
            handler.setFormatter(logging.Formatter("%(message)s"))
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def _log(self, level: int, data: Dict[str, Any]) -> None:
        self.logger.log(level, json.dumps(data, ensure_ascii=False))

    def log_user_action(
        self,
        user_id: int,
        action: str,
        details: Dict[str, Any],
        result: str = "success",
    ) -> None:
        data = {
            "event": "user_action",
            "user_id": user_id,
            "action": action,
            "details": details,
            "result": result,
        }
        self._log(self.USER_ACTION_LEVEL, data)

    def log_participant_operation(
        self,
        user_id: int,
        operation: str,
        participant_data: Dict[str, Any],
        participant_id: Optional[int] = None,
    ) -> None:
        data = {
            "event": "participant_operation",
            "user_id": user_id,
            "operation": operation,
            "participant_data": participant_data,
        }
        if participant_id is not None:
            data["participant_id"] = participant_id
        self._log(self.BUSINESS_LOGIC_LEVEL, data)

    def log_state_transition(
        self,
        user_id: int,
        from_state: str,
        to_state: str,
        context: Dict[str, Any],
    ) -> None:
        data = {
            "event": "state_transition",
            "user_id": user_id,
            "from_state": from_state,
            "to_state": to_state,
            "context": context,
        }
        self._log(self.BUSINESS_LOGIC_LEVEL, data)

    def log_error_with_context(
        self, user_id: int, error: Exception, context: Dict[str, Any], action: str
    ) -> None:
        data = {
            "event": "error",
            "user_id": user_id,
            "error": str(error),
            "context": context,
            "action": action,
        }
        logging.getLogger("errors").error(json.dumps(data, ensure_ascii=False))
