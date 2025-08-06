import logging
from telegram import Update
from telegram.ext import ContextTypes


class LoggingMiddleware:
    def __init__(self):
        self.logger = logging.getLogger("middleware")

    async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.logger.debug("Update received: %s", update)
        return update, context
