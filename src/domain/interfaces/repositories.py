from abc import ABC, abstractmethod
from typing import Protocol


class ParticipantRepositoryInterface(Protocol):
    async def save(self, participant) -> 'Participant':
        ...

    async def find_by_id(self, id: int) -> 'Participant | None':
        ...
