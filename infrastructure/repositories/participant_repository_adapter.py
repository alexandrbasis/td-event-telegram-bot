from domain.interfaces.repositories import ParticipantRepositoryInterface
from domain.models.participant import Participant
from repositories.participant_repository import SqliteParticipantRepository


class ParticipantRepositoryAdapter(ParticipantRepositoryInterface):
    """Адаптер для старого репозитория"""

    def __init__(self, legacy_repository: SqliteParticipantRepository):
        self.legacy_repository = legacy_repository

    async def save(self, participant: Participant) -> Participant | None:
        legacy_participant = participant.to_legacy()
        if participant.id:
            success = self.legacy_repository.update(legacy_participant)
            return participant if success else None
        participant_id = self.legacy_repository.add(legacy_participant)
        participant.id = participant_id
        return participant

    async def find_by_id(self, id: int) -> Participant | None:
        legacy_participant = self.legacy_repository.get_by_id(id)
        return (
            Participant.from_legacy(legacy_participant) if legacy_participant else None
        )

    async def find_by_name(self, name: str) -> Participant | None:
        legacy_participant = self.legacy_repository.get_by_name(name)
        return (
            Participant.from_legacy(legacy_participant) if legacy_participant else None
        )
