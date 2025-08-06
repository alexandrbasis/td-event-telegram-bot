from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes


class MessageService:
    def __init__(self):
        pass

    def _get_return_to_menu_keyboard(self) -> InlineKeyboardMarkup:
        keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data="main_menu")]]
        return InlineKeyboardMarkup(keyboard)

    async def send_response_with_menu_button(
        self, update: Update, text: str, parse_mode: str = "Markdown"
    ) -> None:
        try:
            if update.callback_query:
                await update.callback_query.message.reply_text(
                    text,
                    parse_mode=parse_mode,
                    reply_markup=self._get_return_to_menu_keyboard(),
                )
            else:
                await update.message.reply_text(
                    text,
                    parse_mode=parse_mode,
                    reply_markup=self._get_return_to_menu_keyboard(),
                )
        except Exception:
            if update.callback_query:
                await update.callback_query.message.reply_text(text, parse_mode=parse_mode)
            else:
                await update.message.reply_text(text, parse_mode=parse_mode)

    def add_message_to_cleanup(
        self, context: ContextTypes.DEFAULT_TYPE, message_id: int
    ) -> None:
        if "messages_to_delete" not in context.user_data:
            context.user_data["messages_to_delete"] = []
        context.user_data["messages_to_delete"].append(message_id)
