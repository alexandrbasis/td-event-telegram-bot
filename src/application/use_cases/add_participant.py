from dataclasses import dataclass
from datetime import datetime
import logging

from domain.models.participant import Participant
from domain.services.participant_validator import ParticipantValidator
from domain.services.duplicate_checker import DuplicateCheckerService
from domain.specifications.participant_specifications import (
    TeamRoleRequiresDepartmentSpecification,
)
from domain.interfaces.repositories import ParticipantRepositoryInterface
from shared.event_dispatcher import EventDispatcher
from shared.exceptions import DuplicateParticipantError, ValidationError
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
        duplicate_checker: DuplicateCheckerService,
        event_dispatcher: EventDispatcher,
    ):
        self.repository = repository
        self.validator = validator
        self.duplicate_checker = duplicate_checker
        self.event_dispatcher = event_dispatcher
        self.logger = logging.getLogger(__name__)

    @log_use_case
    async def execute(self, command: AddParticipantCommand) -> Participant:
        """Validate, check duplicates and persist a new participant."""

        validation_result = self.validator.validate(command.participant_data)
        if not validation_result.is_valid:
            raise ValidationError(validation_result.errors)

        existing = await self.duplicate_checker.check_duplicate(
            command.participant_data.get("FullNameRU", "")
        )
        if existing:
            raise DuplicateParticipantError(
                f"Participant '{command.participant_data.get('FullNameRU')}' already exists"
            )

        participant = Participant.from_dict(command.participant_data)
        spec = TeamRoleRequiresDepartmentSpecification()
        if not spec.is_satisfied_by(participant):
            raise ValidationError("Department is required for TEAM role")

        saved = await self.repository.save(participant)
        from domain.events.participant_events import ParticipantAddedEvent

        event = ParticipantAddedEvent(
            participant=saved, added_by=command.user_id, timestamp=datetime.utcnow()
        )
        self.event_dispatcher.dispatch(event)
        return saved
