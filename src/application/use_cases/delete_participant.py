import logging
from dataclasses import dataclass
from typing import Optional

from src.services.participant_service import ParticipantService
from .decorators import log_use_case


@dataclass
class DeleteParticipantCommand:
    participant_id: int
    user_id: Optional[int] = None
    reason: str = ""

    def __post_init__(self):
        if self.participant_id <= 0:
            raise ValueError("participant_id must be positive")


class DeleteParticipantUseCase:
    def __init__(self, participant_service: ParticipantService):
        self.participant_service = participant_service
        self.logger = logging.getLogger(__name__)

    @log_use_case
    async def execute(self, command: DeleteParticipantCommand) -> bool:
        return self.participant_service.delete_participant(
            command.participant_id,
            user_id=command.user_id,
            reason=command.reason,
        )
