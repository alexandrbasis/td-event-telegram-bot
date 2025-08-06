from dataclasses import dataclass
from datetime import datetime
from src.domain.models.participant import Participant


@dataclass(frozen=True)
class ParticipantAddedEvent:
    """Event emitted when a participant is added."""

    participant: Participant
    added_by: int
    timestamp: datetime


@dataclass(frozen=True)
class ParticipantUpdatedEvent:
    """Event emitted when a participant is updated."""

    participant: Participant
    updated_by: int
    timestamp: datetime
