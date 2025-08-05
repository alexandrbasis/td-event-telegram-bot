import logging
from dataclasses import dataclass
from typing import Dict

from services.participant_service import ParticipantService
from domain.services.participant_validator import ParticipantValidator
from domain.models.participant import Participant
from shared.exceptions import ValidationError
from .decorators import log_use_case


@dataclass
class UpdateParticipantCommand:
    participant_id: int
    user_id: int
    participant_data: Dict

    def __post_init__(self):
        if self.participant_id <= 0:
            raise ValueError("participant_id must be positive")
        if not self.participant_data:
            raise ValueError("participant_data must not be empty")


class UpdateParticipantUseCase:
    def __init__(
        self,
        participant_service: ParticipantService,
        validator: ParticipantValidator,
    ):
        self.participant_service = participant_service
        self.validator = validator
        self.logger = logging.getLogger(__name__)

    @log_use_case
    async def execute(self, command: UpdateParticipantCommand) -> Participant | None:
        validation_result = self.validator.validate(command.participant_data)
        if not validation_result.is_valid:
            raise ValidationError(validation_result.errors)
        return self.participant_service.update_participant(
            command.participant_id,
            command.participant_data,
            user_id=command.user_id,
        )
