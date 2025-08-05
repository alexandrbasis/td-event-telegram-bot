import logging
from functools import wraps


def log_use_case(func):
    """Simple decorator to log use case execution start and end."""

    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        logger = getattr(self, "logger", None) or logging.getLogger(self.__class__.__name__)
        logger.debug(f"Executing use case {self.__class__.__name__}")
        result = await func(self, *args, **kwargs)
        logger.debug(f"Completed use case {self.__class__.__name__}")
        return result

    return wrapper
