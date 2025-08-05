from typing import Protocol


class ParticipantRepositoryInterface(Protocol):
    async def save(self, participant) -> "Participant | None":
        ...

    async def find_by_id(self, id: int) -> "Participant | None":
        ...
