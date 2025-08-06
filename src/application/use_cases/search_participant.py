import logging
from dataclasses import dataclass
from typing import List, Optional

from ...services.participant_service import ParticipantService, SearchResult
from .decorators import log_use_case


@dataclass
class SearchParticipantsQuery:
    query: str
    max_results: int = 5
    user_id: Optional[int] = None

    def __post_init__(self):
        if not self.query or not self.query.strip():
            raise ValueError("query must not be empty")
        if self.max_results <= 0:
            raise ValueError("max_results must be positive")


class SearchParticipantsUseCase:
    def __init__(self, participant_service: ParticipantService):
        self.participant_service = participant_service
        self.logger = logging.getLogger(__name__)

    @log_use_case
    async def execute(self, query: SearchParticipantsQuery) -> List[SearchResult]:
        return self.participant_service.search_participants(
            query.query, max_results=query.max_results
        )
