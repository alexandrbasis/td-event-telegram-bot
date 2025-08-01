import time


def set_edit_timeout(context, user_id, timeout_seconds=300):
    """Устанавливает таймаут для редактирования поля."""
    context.user_data["edit_timeout"] = time.time() + timeout_seconds


def is_edit_expired(context):
    """Проверяет, истек ли таймаут редактирования."""
    timeout = context.user_data.get("edit_timeout")
    return bool(timeout and time.time() > timeout)


def clear_expired_edit(context):
    """Очищает просроченное поле редактирования."""
    if is_edit_expired(context):
        context.user_data.pop("field_to_edit", None)
        context.user_data.pop("edit_timeout", None)
        return True
    return False
