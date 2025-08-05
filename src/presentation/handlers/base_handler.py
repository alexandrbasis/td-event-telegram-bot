from abc import ABC, abstractmethod
from telegram import Update
from telegram.ext import ContextTypes


class BaseHandler(ABC):
    def __init__(self, container):
        self.container = container
        self.logger = container.logger() if hasattr(container, "logger") else None

    @abstractmethod
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle an incoming update."""
        raise NotImplementedError

    async def handle_with_logging(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Wrapper для логирования"""
        user_id = update.effective_user.id

        if self.logger:
            self.logger.info(
                f"Handler {self.__class__.__name__} called by user {user_id}"
            )

        try:
            return await self.handle(update, context)
        except Exception as e:  # pragma: no cover - logging side effects
            if self.logger:
                self.logger.error(
                    f"Error in {self.__class__.__name__}: {e}", exc_info=True
                )
            raise
