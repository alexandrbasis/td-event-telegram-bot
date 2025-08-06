from telegram import Update
from telegram.ext import ContextTypes

from ..use_cases.add_participant import AddParticipantCommand
from ..use_cases.update_participant import UpdateParticipantCommand
from ..use_cases.search_participant import SearchParticipantsQuery
from ...shared.exceptions import ValidationError
from ...presentation.ui import UIFactory
from ...states import COLLECTING_DATA

MAIN_MENU = 0


class ParticipantController:
    """Coordinates participant flows using use cases and UI factories."""

    def __init__(self, container):
        self.add_use_case = container.add_participant_use_case()
        self.update_use_case = container.update_participant_use_case()
        self.search_use_case = container.search_participants_use_case()
        self.ui_factory: UIFactory = container.ui_factory()

    async def start_add_flow(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = self.ui_factory.create_add_participant_form()
        await update.message.reply_text(
            "\u2795 Добавление участника", reply_markup=keyboard
        )
        return COLLECTING_DATA

    async def handle_add_data(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, participant_data: dict
    ):
        try:
            command = AddParticipantCommand(
                user_id=update.effective_user.id, participant_data=participant_data
            )
            participant = await self.add_use_case.execute(command)
            message = f"✅ Участник '{participant.full_name_ru}' добавлен"
            keyboard = self.ui_factory.create_success_keyboard()
            await update.message.reply_text(message, reply_markup=keyboard)
            return MAIN_MENU
        except ValidationError as exc:
            from presentation.ui.components.validation_ui import show_validation_errors

            await show_validation_errors(update, exc.errors)
            return COLLECTING_DATA

    async def handle_update(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        participant_id: int,
        participant_data: dict,
    ):
        command = UpdateParticipantCommand(
            user_id=update.effective_user.id,
            participant_id=participant_id,
            participant_data=participant_data,
        )
        participant = await self.update_use_case.execute(command)
        await update.message.reply_text(
            f"✏️ Участник '{participant.full_name_ru}' обновлен"
        )
        return MAIN_MENU

    async def search(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE, query: str
    ):
        results = await self.search_use_case.execute(
            SearchParticipantsQuery(query, user_id=update.effective_user.id)
        )
        lines = [
            f"{r.participant.FullNameRU} (ID: {r.participant.id})" for r in results
        ]
        text = "\n".join(lines) or "❌ Ничего не найдено"
        await update.message.reply_text(text)
        return MAIN_MENU
