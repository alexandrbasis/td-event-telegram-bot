from telegram import Update
from telegram.ext import ContextTypes

from presentation.handlers.base_handler import BaseHandler


class StartCommandHandler(BaseHandler):
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Пока просто вызываем старую логику
        from main import start_command

        return await start_command(update, context)
