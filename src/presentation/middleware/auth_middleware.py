import logging
from telegram import Update
from telegram.ext import ContextTypes


class AuthMiddleware:
    def __init__(self, container):
        self.container = container
        self.logger = logging.getLogger(__name__)

    async def __call__(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        # Simple auth check placeholder
        allowed_ids = self.container.config.telegram.get("allowed_ids", [])
        if allowed_ids and user_id not in allowed_ids:
            await update.message.reply_text("❌ Доступ запрещен")
            return None
        self.logger.info("User %s passed auth", user_id)
        return update, context
