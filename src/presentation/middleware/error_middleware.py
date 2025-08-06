import logging
from telegram import Update
from telegram.ext import ContextTypes


class ErrorMiddleware:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            return update, context
        except Exception as exc:  # pragma: no cover - simple example
            self.logger.exception("Unhandled error: %s", exc)
            if update and update.message:
                await update.message.reply_text("⚠️ Произошла ошибка")
            return None
