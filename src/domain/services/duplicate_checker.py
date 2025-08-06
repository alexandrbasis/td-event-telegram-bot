from src.domain.interfaces.repositories import ParticipantRepositoryInterface
from src.domain.models.participant import Participant
from typing import Optional


class DuplicateCheckerService:
    """Domain service for detecting duplicate participants."""

    def __init__(self, repository: ParticipantRepositoryInterface):
        self.repository = repository

    async def check_duplicate(self, full_name_ru: str) -> Optional[Participant]:
        """Return existing participant with given full name if present."""
        return await self.repository.find_by_name(full_name_ru)
