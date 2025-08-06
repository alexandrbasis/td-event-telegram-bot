from dataclasses import asdict
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from src.presentation.handlers.base_handler import BaseHandler
from src.utils.decorators import require_role
from src.presentation.ui.formatters import MessageFormatter
from src.states import COLLECTING_DATA, CONFIRMING_DUPLICATE
from src.messages import MESSAGES
from src.application.use_cases.add_participant import AddParticipantCommand
from src.application.use_cases.update_participant import UpdateParticipantCommand
from src.application.use_cases.search_participant import SearchParticipantsQuery


class AddCallbackHandler(BaseHandler):
    def __init__(self, container, message_service):
        super().__init__(container)
        self.message_service = message_service
        self._handle = require_role("coordinator")(self._handle)

    async def _handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        query = update.callback_query
        await query.answer()
        await query.edit_message_reply_markup(reply_markup=None)

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

        msg1 = await query.message.reply_text(
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
        msg2 = await query.message.reply_text(MESSAGES["ADD_TEMPLATE"])
        self.message_service.add_message_to_cleanup(context, msg1.message_id)
        self.message_service.add_message_to_cleanup(context, msg2.message_id)
        self.message_service.add_message_to_cleanup(context, query.message.message_id)
        context.user_data["current_state"] = COLLECTING_DATA
        return COLLECTING_DATA

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        return await self._handle(update, context)


class SearchCallbackHandler(BaseHandler):
    def __init__(self, container, ui_service):
        super().__init__(container)
        self.search_use_case = (
            container.search_participants_use_case()
            if hasattr(container, "search_participants_use_case")
            else None
        )
        self.ui_service = ui_service
        self._handle = require_role("viewer")(self._handle)

    async def _handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.effective_user.id
        if self.logger:
            self.logger.info(f"🔍 handle_search_callback called for user {user_id}")
            self.logger.debug(
                f"user_data before search: {list(context.user_data.keys())}"
            )

        if context.user_data:
            if self.logger:
                self.logger.warning(
                    f"Found existing user_data during search start: {list(context.user_data.keys())}"
                )
            context.user_data.clear()

        if self.user_logger:
            self.user_logger.log_user_action(user_id, "search_callback_triggered", {})

        return await self.ui_service.show_search_prompt(
            update, context, is_callback=True
        )

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        return await self._handle(update, context)


class MainMenuCallbackHandler(BaseHandler):
    def __init__(self, container, ui_service, message_service):
        super().__init__(container)
        self.ui_service = ui_service
        self.message_service = message_service
        self._handle = require_role("viewer")(self._handle)

    async def _handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        user_id = update.effective_user.id
        if self.user_logger:
            self.user_logger.log_user_action(user_id, "menu_action", {"action": data})

        await query.edit_message_reply_markup(reply_markup=None)

        if data == "main_cancel":
            from main import cancel_callback

            return await cancel_callback(update, context)

        if data == "main_menu":
            await self.ui_service.show_main_menu(update, context, is_return=True)
            return

        if data == "main_list":
            participants = self.participant_service.get_all_participants()
            if not participants:
                empty_keyboard = InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "➕ Добавить участника", callback_data="main_add"
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "🏠 Главное меню", callback_data="main_menu"
                            )
                        ],
                    ]
                )

                await query.message.reply_text(
                    "📋 **Список участников пуст**\n\nДобавьте первого участника:",
                    parse_mode="Markdown",
                    reply_markup=empty_keyboard,
                )
                return

            message = f"📋 **Список участников ({len(participants)} чел.):**\n\n"
            for p in participants:
                role_emoji = "👤" if p.Role == "CANDIDATE" else "👨‍💼"
                department = (
                    f" ({p.Department})" if p.Role == "TEAM" and p.Department else ""
                )
                message += f"{role_emoji} **{p.FullNameRU}**\n"
                message += f"   • Роль: {p.Role}{department}\n"
                message += f"   • ID: {p.id}\n\n"

            await self.message_service.send_response_with_menu_button(update, message)
            return

        if data == "main_export":
            await self.message_service.send_response_with_menu_button(
                update,
                "📤 **Экспорт данных** (заглушка)\n\n"
                "🔧 Функция в разработке.\n"
                "Пример: /export worship team - экспорт участников worship команды",
            )
            return

        if data == "main_help":
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

            await self.message_service.send_response_with_menu_button(update, help_text)
            return

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        return await self._handle(update, context)


class SaveConfirmationCallbackHandler(BaseHandler):
    def __init__(self, container, ui_service):
        super().__init__(container)
        self.ui_service = ui_service
        from main import smart_cleanup_on_error, log_state_transitions

        self.add_use_case = container.add_participant_use_case()
        self.update_use_case = container.update_participant_use_case()
        self.search_use_case = container.search_participants_use_case()
        self.get_use_case = container.get_participant_use_case()

        self._handle = require_role("coordinator")(
            smart_cleanup_on_error(log_state_transitions(self._handle))
        )

    async def _handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        from main import (
            cleanup_user_data_safe,
            get_duplicate_keyboard,
            format_participant_full_info,
        )

        query = update.callback_query
        user_id = update.effective_user.id

        if self.logger:
            self.logger.info(f"Save confirmation requested by user {user_id}")
            self.logger.debug(f"callback_data: {query.data}")
            self.logger.debug(f"user_data keys: {list(context.user_data.keys())}")

        await query.answer()
        await self.ui_service.cleanup_messages(context, update.effective_chat.id)

        participant_data = context.user_data.get("parsed_participant", {})
        if not participant_data:
            await query.message.reply_text(
                "❌ Не удалось найти данные для сохранения. Попробуйте снова."
            )
            cleanup_user_data_safe(context, update.effective_user.id)
            return ConversationHandler.END

        is_update = "participant_id" in context.user_data

        if not is_update:
            name = participant_data.get("FullNameRU")
            existing = None
            if name:
                results = await self.search_use_case.execute(
                    SearchParticipantsQuery(name, max_results=1, user_id=user_id)
                )
                if results:
                    existing = results[0].participant
            if existing and existing.FullNameRU.lower() == name.lower():
                context.user_data["existing_participant_id"] = existing.id
                message = "⚠️ **Найден дубликат!**\n\n"
                message += MessageFormatter.format_participant_info(asdict(existing))
                message += "\n\nЧто делаем?"
                await query.message.reply_text(
                    message,
                    parse_mode="Markdown",
                    reply_markup=get_duplicate_keyboard(),
                )
                return CONFIRMING_DUPLICATE

        try:
            if is_update:
                participant_id = context.user_data["participant_id"]
                await self.update_use_case.execute(
                    UpdateParticipantCommand(
                        participant_id=participant_id,
                        user_id=user_id,
                        participant_data=participant_data,
                    )
                )
                if self.user_logger:
                    self.user_logger.log_participant_operation(
                        user_id, "update", participant_data, participant_id
                    )
                    self.user_logger.log_user_action(
                        user_id,
                        "command_end",
                        {
                            "command": "/add",
                            "participant_id": participant_id,
                            "result": "updated",
                        },
                    )
                updated_participant = await self.get_use_case.execute(participant_id)
                if updated_participant:
                    full_info = format_participant_full_info(
                        asdict(updated_participant)
                    )
                    success_message = f"✅ **Участник обновлен!**\n\n{full_info}"
                else:
                    success_message = (
                        f"✅ **Участник {participant_data['FullNameRU']} (ID: {participant_id})"
                        " успешно обновлен!**"
                    )
            else:
                new_participant = await self.add_use_case.execute(
                    AddParticipantCommand(
                        user_id=user_id, participant_data=participant_data
                    )
                )
                if self.user_logger:
                    self.user_logger.log_participant_operation(
                        user_id, "add", participant_data, new_participant.id
                    )
                    self.user_logger.log_user_action(
                        user_id,
                        "command_end",
                        {
                            "command": "/add",
                            "participant_id": new_participant.id,
                            "result": "added",
                        },
                    )
                full_info = format_participant_full_info(asdict(new_participant))
                success_message = f"✅ **Участник добавлен!**\n\n{full_info}"
        except Exception:
            raise

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✏️ Редактировать",
                        callback_data=(
                            f"edit_participant_{new_participant.id}"
                            if not is_update
                            else f"edit_participant_{participant_id}"
                        ),
                    ),
                    InlineKeyboardButton("➕ Добавить еще", callback_data="main_add"),
                ],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")],
            ]
        )

        await query.message.reply_text(
            success_message,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )

        cleanup_user_data_safe(context, update.effective_user.id)
        return ConversationHandler.END

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        return await self._handle(update, context)


class DuplicateCallbackHandler(BaseHandler):
    def __init__(self, container):
        super().__init__(container)
        from main import smart_cleanup_on_error, log_state_transitions

        self._handle = smart_cleanup_on_error(log_state_transitions(self._handle))

    async def _handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        from main import cleanup_user_data_safe, get_post_action_keyboard

        query = update.callback_query
        await query.answer()

        action = query.data
        participant_data = context.user_data.get("parsed_participant", {})
        user_id = update.effective_user.id if update.effective_user else 0

        if action == "dup_add_new":
            try:
                new_participant = self.participant_service.add_participant(
                    participant_data, user_id=user_id
                )
                if self.user_logger:
                    self.user_logger.log_participant_operation(
                        user_id, "add", participant_data, new_participant.id
                    )
                    self.user_logger.log_user_action(
                        user_id,
                        "command_end",
                        {
                            "command": "/add",
                            "participant_id": new_participant.id,
                            "result": "added_duplicate",
                        },
                    )
            except Exception as e:
                raise
            cleanup_user_data_safe(context, update.effective_user.id)

            await query.message.reply_text(
                f"✅ **Участник добавлен как новый (возможен дубль)**\n\n"
                f"🆔 ID: {new_participant.id}\n"
                f"👤 Имя: {participant_data['FullNameRU']}\n\n"
                f"⚠️ Обратите внимание на возможное дублирование!",
                parse_mode="Markdown",
                reply_markup=get_post_action_keyboard(),
            )

        elif action == "dup_replace":
            existing = self.participant_service.check_duplicate(
                participant_data["FullNameRU"], user_id=user_id
            )
            if existing:
                try:
                    updated = self.participant_service.update_participant(
                        existing.id, participant_data, user_id=user_id
                    )
                    if self.user_logger:
                        self.user_logger.log_participant_operation(
                            user_id, "update", participant_data, existing.id
                        )
                        self.user_logger.log_user_action(
                            user_id,
                            "command_end",
                            {
                                "command": "/add",
                                "participant_id": existing.id,
                                "result": "updated_duplicate",
                            },
                        )
                except Exception:
                    raise
                cleanup_user_data_safe(context, update.effective_user.id)

                if updated:
                    await query.message.reply_text(
                        f"🔄 **Участник обновлен!**\n\n"
                        f"🆔 ID: {existing.id}\n"
                        f"👤 Имя: {participant_data['FullNameRU']}\n"
                        f"👥 Роль: {participant_data['Role']}\n\n"
                        f"📋 Данные заменены новыми значениями",
                        parse_mode="Markdown",
                        reply_markup=get_post_action_keyboard(),
                    )
                else:
                    await query.message.reply_text("❌ Ошибка обновления участника.")
            else:
                await query.message.reply_text("❌ Существующий участник не найден.")

        return ConversationHandler.END

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        return await self._handle(update, context)
