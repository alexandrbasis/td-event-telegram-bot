from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from application.use_cases.search_participant import SearchParticipantsQuery
from application.use_cases.update_participant import UpdateParticipantCommand
from presentation.handlers.base_handler import BaseHandler
from utils.decorators import require_role
from utils.session_recovery import detect_interrupted_session, handle_session_recovery
from messages import MESSAGES
from states import COLLECTING_DATA
from main import (
    _cleanup_messages,
    _show_main_menu,
    _record_action,
    _log_session_end,
    _send_response_with_menu_button,
    _show_search_prompt,
)
from presentation.ui.formatters.participant_formatter import format_participant


class StartCommandHandler(BaseHandler):
    def __init__(self, container):
        super().__init__(container)
        self._handle = require_role("viewer")(self._handle)

    async def _handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if detect_interrupted_session(update, context):
            await handle_session_recovery(update, context)
            return

        _log_session_end(context, user_id)
        context.user_data["session_start"] = datetime.utcnow()
        if self.user_logger:
            self.user_logger.log_user_action(
                user_id, "command_start", {"command": "/start"}
            )
        _record_action(context, "/start:start")

        if self.logger:
            self.logger.info("User %s started /start", user_id)
        await _cleanup_messages(context, update.effective_chat.id)
        await _show_main_menu(update, context)
        if self.user_logger:
            self.user_logger.log_user_action(
                user_id, "command_end", {"command": "/start"}
            )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        return await self._handle(update, context)


class AddCommandHandler(BaseHandler):
    def __init__(self, container):
        super().__init__(container)
        from main import cleanup_on_error

        self._handle = require_role("coordinator")(
            cleanup_on_error(self._handle)
        )

    async def _handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        if detect_interrupted_session(update, context):
            await handle_session_recovery(update, context)
            return

        if self.user_logger:
            self.user_logger.log_user_action(
                user_id, "command_start", {"command": "/add"}
            )
        _record_action(context, "/add:start")

        context.user_data["add_flow_data"] = {
            "FullNameRU": None,
            "Gender": None,
            "Size": None,
            "Church": None,
            "Role": None,
            "Department": None,
            "FullNameEN": None,
            "CountryAndCity": None,
            "SubmittedBy": None,
            "ContactInformation": None,
        }

        cancel_markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton("❌ Отмена", callback_data="main_cancel")]]
        )

        msg1 = await update.message.reply_text(
            "🚀 **Начинаем добавлять нового участника.**\n\n"
            "Отправьте данные любым удобным способом:\n"
            "1️⃣ **Вставьте заполненный шаблон** (пришлю его следующим сообщением).\n"
            "2️⃣ **Отправьте несколько полей**, разделяя их запятой (`,`) или каждое с новой строки.\n"
            "3️⃣ **Отправляйте по одному полю** в сообщении (например, `Церковь Грейс`).\n\n"
            "*Для самой точной обработки используйте запятые или ввод с новой строки.*\n"
            "Для отмены введите /cancel.",
            parse_mode="Markdown",
            reply_markup=cancel_markup,
        )
        msg2 = await update.message.reply_text(MESSAGES["ADD_TEMPLATE"])
        from main import _add_message_to_cleanup

        _add_message_to_cleanup(context, msg1.message_id)
        _add_message_to_cleanup(context, msg2.message_id)
        _add_message_to_cleanup(context, update.message.message_id)
        context.user_data["current_state"] = COLLECTING_DATA
        if self.user_logger:
            self.user_logger.log_state_transition(
                user_id, "START", str(COLLECTING_DATA), {}
            )
        return COLLECTING_DATA

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        return await self._handle(update, context)



class UpdateParticipantHandler(BaseHandler):
    def __init__(self, container):
        super().__init__(container)
        self.update_use_case = container.update_participant_use_case()
        self._handle = require_role("coordinator")(self._handle)

    async def _handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        participant_id = context.user_data.get("participant_id")
        data = context.user_data.get("parsed_participant", {})
        if participant_id is None:
            await update.message.reply_text("❌ Участник не выбран")
            return
        command = UpdateParticipantCommand(user_id=user_id, participant_id=participant_id, participant_data=data)
        participant = await self.update_use_case.execute(command)
        await update.message.reply_text(f"✏️ Участник '{participant.full_name_ru}' обновлен")

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        return await self._handle(update, context)

class HelpCommandHandler(BaseHandler):
    def __init__(self, container):
        super().__init__(container)
        self._handle = require_role("viewer")(self._handle)

    async def _handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if detect_interrupted_session(update, context):
            await handle_session_recovery(update, context)
            return

        if self.user_logger:
            self.user_logger.log_user_action(
                user_id, "command_start", {"command": "/help"}
            )
        _record_action(context, "/help:start")
        from main import get_user_role

        role = get_user_role(user_id)
        if self.logger:
            self.logger.info("User %s requested help", user_id)

        help_text = """
📖 **Справка по командам:**

👥 **Управление участниками:**
/add - Добавить нового участника
/edit - Редактировать данные участника
/delete - Удалить участника

📊 **Просмотр данных:**
/list - Показать список участников
/export - Экспорт данных в CSV

❓ **Помощь:**
/help - Показать эту справку
/start - Главное меню
/cancel - Отменить текущую операцию

🔍 **Примеры запросов (скоро):**
"Сколько team-member в worship?"
"Кто живет в комнате 203A?"
        """

        await _send_response_with_menu_button(update, help_text)
        if self.user_logger:
            self.user_logger.log_user_action(
                user_id, "command_end", {"command": "/help"}
            )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        return await self._handle(update, context)


class ListCommandHandler(BaseHandler):
    def __init__(self, container):
        super().__init__(container)
        self.list_use_case = container.list_participants_use_case()
        self._handle = require_role("viewer")(self._handle)

    async def _handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if detect_interrupted_session(update, context):
            await handle_session_recovery(update, context)
            return

        if self.user_logger:
            self.user_logger.log_user_action(
                user_id, "command_start", {"command": "/list"}
            )
        participants = await self.list_use_case.execute()

        if not participants:
            keyboard = self.ui_factory.create_add_participant_form()
            await update.message.reply_text(
                "📋 **Список участников пуст**\n\nДобавьте первого участника:",
                parse_mode="Markdown",
                reply_markup=keyboard,
            )
            if self.user_logger:
                self.user_logger.log_user_action(
                    user_id, "command_end", {"command": "/list", "count": 0}
                )
            return

        lines = [format_participant(p) for p in participants]
        message = "📋 **Список участников:**\n\n" + "\n".join(
            f"- {line}" for line in lines
        )
        keyboard = self.ui_factory.create_success_keyboard()
        await update.message.reply_text(
            message, parse_mode="Markdown", reply_markup=keyboard
        )

        if self.user_logger:
            self.user_logger.log_user_action(
                user_id,
                "command_end",
                {"command": "/list", "count": len(participants)},
            )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        return await self._handle(update, context)


class SearchCommandHandler(BaseHandler):
    def __init__(self, container):
        super().__init__(container)
        self.search_use_case = container.search_participants_use_case()
        self._handle = require_role("viewer")(self._handle)

    async def _handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        if detect_interrupted_session(update, context):
            await handle_session_recovery(update, context)
            return

        if self.user_logger:
            self.user_logger.log_user_action(
                user_id, "command_start", {"command": "/search"}
            )
        _record_action(context, "/search:start")
        text = update.message.text or ""
        parts = text.split(maxsplit=1)
        if len(parts) > 1:
            query_text = parts[1]
            results = await self.search_use_case.execute(SearchParticipantsQuery(query_text, user_id=user_id))
            if results:
                formatted = [f"- {r.participant.FullNameRU} (ID: {r.participant.id})" for r in results]
                message = "\n".join(formatted)
            else:
                message = "❌ Ничего не найдено"
            await _send_response_with_menu_button(update, message)
            if self.user_logger:
                self.user_logger.log_user_action(user_id, "command_end", {"command": "/search", "count": len(results)})
            return ConversationHandler.END
        return await _show_search_prompt(update, context, is_callback=False)

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        return await self._handle(update, context)


class CancelCommandHandler(BaseHandler):
    def __init__(self, container):
        super().__init__(container)
        self._handle = require_role("viewer")(self._handle)

    async def _handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        if detect_interrupted_session(update, context):
            await handle_session_recovery(update, context)
            return

        if self.user_logger:
            self.user_logger.log_user_action(
                user_id, "command_start", {"command": "/cancel"}
            )
        _record_action(context, "/cancel:start")
        _log_session_end(context, user_id)
        if context.user_data:
            context.user_data.clear()
            if self.logger:
                self.logger.info("User %s cancelled the add flow.", user_id)
        else:
            if self.logger:
                self.logger.info(
                    "User %s cancelled a non-existent operation.", user_id
                )

        await _cleanup_messages(context, update.effective_chat.id)
        await _show_main_menu(update, context, is_return=True)
        if self.user_logger:
            self.user_logger.log_user_action(
                user_id, "command_end", {"command": "/cancel"}
            )
        return ConversationHandler.END

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        return await self._handle(update, context)
