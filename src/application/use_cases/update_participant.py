import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict

from domain.services.participant_validator import ParticipantValidator
from domain.services.duplicate_checker import DuplicateCheckerService
from models.participant import Participant
from domain.specifications.participant_specifications import (
    TeamRoleRequiresDepartmentSpecification,
)
from domain.interfaces.repositories import ParticipantRepositoryInterface
from shared.event_dispatcher import EventDispatcher
from shared.exceptions import ValidationError, DuplicateParticipantError
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
    async def execute(self, command: UpdateParticipantCommand) -> Participant | None:
        """Update participant with validation and duplicate checking."""

        validation_result = self.validator.validate(command.participant_data)
        if not validation_result.is_valid:
            raise ValidationError(validation_result.errors)

        existing = await self.repository.find_by_id(command.participant_id)
        if existing is None:
            return None

        new_name = command.participant_data.get("FullNameRU")
        if new_name and new_name != existing.full_name_ru:
            duplicate = await self.duplicate_checker.check_duplicate(new_name)
            if duplicate and duplicate.id != existing.id:
                raise DuplicateParticipantError(
                    f"Participant '{new_name}' already exists"
                )

        existing_dict = asdict(existing)
        merged_data = {**existing_dict, **command.participant_data}
        updated_participant = Participant.from_dict(merged_data)

        spec = TeamRoleRequiresDepartmentSpecification()
        if not spec.is_satisfied_by(updated_participant):
            raise ValidationError("Department is required for TEAM role")

        result = await self.repository.save(updated_participant)
        if result:
            from domain.events.participant_events import ParticipantUpdatedEvent

            event = ParticipantUpdatedEvent(
                participant=result,
                updated_by=command.user_id,
                timestamp=datetime.utcnow(),
            )
            self.event_dispatcher.dispatch(event)
            return result

        return None
