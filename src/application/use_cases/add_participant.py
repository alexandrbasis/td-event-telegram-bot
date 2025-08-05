from dataclasses import dataclass

import logging

from domain.models.participant import Participant
from domain.services.participant_validator import ParticipantValidator
from domain.interfaces.repositories import ParticipantRepositoryInterface
from shared.exceptions import ValidationError
from .decorators import log_use_case


@dataclass
class AddParticipantCommand:
    user_id: int
    participant_data: dict


class AddParticipantUseCase:
    def __init__(
        self,
        repository: ParticipantRepositoryInterface,
        validator: ParticipantValidator,
    ):
        self.repository = repository
        self.validator = validator
        self.logger = logging.getLogger(__name__)

    @log_use_case
    async def execute(self, command: AddParticipantCommand) -> Participant:
        """Validate and persist a new participant."""

        validation_result = self.validator.validate(command.participant_data)
        if not validation_result.is_valid:
            raise ValidationError(validation_result.errors)

        participant = Participant.from_dict(command.participant_data)
        return await self.repository.save(participant)

