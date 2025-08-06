from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from config import COORDINATOR_IDS, VIEWER_IDS
from states import SEARCHING_PARTICIPANTS
from presentation.services.message_service import MessageService


class UIService:
    def __init__(self, message_service: MessageService):
        self.message_service = message_service

    def _get_user_role(self, user_id: int) -> str:
        if user_id in COORDINATOR_IDS:
            return "coordinator"
        if user_id in VIEWER_IDS:
            return "viewer"
        return "unauthorized"

    async def cleanup_messages(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
        messages_to_delete = context.user_data.get("messages_to_delete", [])
        for message_id in messages_to_delete:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            except Exception:
                continue
        if "messages_to_delete" in context.user_data:
            context.user_data["messages_to_delete"].clear()

    def get_main_menu_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        if user_id in COORDINATOR_IDS:
            keyboard = [
                [
                    InlineKeyboardButton("➕ Добавить", callback_data="main_add"),
                    InlineKeyboardButton("🔍 Поиск", callback_data="main_search"),
                ],
                [
                    InlineKeyboardButton("📋 Список", callback_data="main_list"),
                    InlineKeyboardButton("📤 Экспорт", callback_data="main_export"),
                ],
                [InlineKeyboardButton("ℹ️ Помощь", callback_data="main_help")],
            ]
        else:
            keyboard = [
                [
                    InlineKeyboardButton("🔍 Поиск", callback_data="main_search"),
                    InlineKeyboardButton("📋 Список", callback_data="main_list"),
                ],
                [
                    InlineKeyboardButton("📤 Экспорт", callback_data="main_export"),
                    InlineKeyboardButton("ℹ️ Помощь", callback_data="main_help"),
                ],
            ]
        return InlineKeyboardMarkup(keyboard)

    async def show_main_menu(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, is_return: bool = False
    ) -> None:
        user_id = update.effective_user.id
        role = self._get_user_role(user_id)
        if is_return:
            if context.user_data:
                context.user_data.clear()
            if hasattr(context, "chat_data") and context.chat_data:
                conversation_keys = [
                    k for k in list(context.chat_data.keys()) if "conversation" in str(k).lower()
                ]
                for key in conversation_keys:
                    context.chat_data.pop(key, None)

        if is_return:
            welcome_text = "✅ **Операция завершена.**\n\nЧем еще могу вам помочь?"
        else:
            welcome_text = (
                "🏕️ **Добро пожаловать в бот Tres Dias Israel!**\n\n"
                f"👤 Ваша роль: **{role.title()}**"
            )

        reply_markup = self.get_main_menu_keyboard(user_id)

        if update.callback_query:
            try:
                await update.callback_query.edit_message_text(
                    text=welcome_text,
                    parse_mode="Markdown",
                    reply_markup=reply_markup,
                )
            except Exception:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=welcome_text,
                    parse_mode="Markdown",
                    reply_markup=reply_markup,
                )
        else:
            await update.effective_message.reply_text(
                text=welcome_text, parse_mode="Markdown", reply_markup=reply_markup
            )

    async def show_search_prompt(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback: bool = False
    ) -> int:
        """Показать промпт для ввода поискового запроса."""
        cancel_markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton("❌ Отмена", callback_data="main_cancel")]]
        )

        text = (
            "🔍 **Поиск участников**\n\n"
            "Введите для поиска:\n"
            "• **Имя** (русское или английское)\n"
            "• **ID участника** (например: 123)\n"
            "• **Часть имени** (например: Иван)\n\n"
            "💡 *Поиск поддерживает нечеткое совпадение*"
        )

        if is_callback:
            await update.callback_query.answer()
            await update.callback_query.edit_message_reply_markup(reply_markup=None)
            msg = await update.callback_query.message.reply_text(
                text, parse_mode="Markdown", reply_markup=cancel_markup
            )
            self.message_service.add_message_to_cleanup(
                context, update.callback_query.message.message_id
            )
        else:
            msg = await update.message.reply_text(
                text, parse_mode="Markdown", reply_markup=cancel_markup
            )
            self.message_service.add_message_to_cleanup(
                context, update.message.message_id
            )

        self.message_service.add_message_to_cleanup(context, msg.message_id)
        context.user_data["current_state"] = SEARCHING_PARTICIPANTS
        return SEARCHING_PARTICIPANTS
