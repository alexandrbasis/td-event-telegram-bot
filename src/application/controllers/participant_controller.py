from telegram import Update
from telegram.ext import ContextTypes

from application.use_cases.add_participant import (
    AddParticipantCommand,
    AddParticipantUseCase,
)
from shared.exceptions import ValidationError
from utils.user_logger import UserActionLogger


class ParticipantController:
    def __init__(self, add_use_case: AddParticipantUseCase):
        self.add_use_case = add_use_case
        self.user_logger = UserActionLogger()

    async def handle_add_participant(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Обработка добавления участника."""

        user_id = update.effective_user.id
        self.user_logger.log_user_action(
            user_id, "command_start", {"command": "/add"}
        )

        try:
            command = AddParticipantCommand(
                user_id=user_id,
                participant_data=context.user_data.get("parsed_participant", {}),
            )

            participant = await self.add_use_case.execute(command)

            self.user_logger.log_user_action(
                user_id, "command_end", {"command": "/add"}
            )
            await update.message.reply_text(
                f"✅ Участник {participant.full_name_ru} добавлен!"
            )

        except ValidationError as e:
            self.user_logger.log_user_action(
                user_id,
                "command_end",
                {"command": "/add", "result": "error", "errors": e.errors},
            )
            await update.message.reply_text(
                f"❌ Ошибка валидации: {'; '.join(e.errors)}"
            )

