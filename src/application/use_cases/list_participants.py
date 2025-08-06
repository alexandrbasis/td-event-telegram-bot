import logging
from typing import List

from ...services.participant_service import ParticipantService
from src.models.participant import Participant
from .decorators import log_use_case


class ListParticipantsUseCase:
    def __init__(self, participant_service: ParticipantService):
        self.participant_service = participant_service
        self.logger = logging.getLogger(__name__)

    @log_use_case
    async def execute(self) -> List[Participant]:
        return self.participant_service.get_all_participants()
