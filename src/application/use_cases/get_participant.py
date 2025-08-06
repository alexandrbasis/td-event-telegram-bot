import logging

from ...services.participant_service import ParticipantService
from models.participant import Participant
from .decorators import log_use_case


class GetParticipantUseCase:
    def __init__(self, participant_service: ParticipantService):
        self.participant_service = participant_service
        self.logger = logging.getLogger(__name__)

    @log_use_case
    async def execute(self, participant_id: int) -> Participant | None:
        if participant_id <= 0:
            raise ValueError("participant_id must be positive")
        return self.participant_service.get_participant(participant_id)
