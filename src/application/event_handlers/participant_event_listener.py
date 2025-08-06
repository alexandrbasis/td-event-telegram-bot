import logging

from src.domain.events.participant_events import (
    ParticipantAddedEvent,
    ParticipantUpdatedEvent,
)


class ParticipantEventListener:
    """Обработчик событий участников."""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def on_participant_added(self, event: ParticipantAddedEvent) -> None:
        """Обработка события добавления участника."""
        self.logger.info(
            f"🎉 Participant added: {event.participant.full_name_ru}",
            extra={
                "event_type": "participant_added",
                "participant_id": event.participant.id,
                "participant_name": event.participant.full_name_ru,
                "participant_role": event.participant.role,
                "added_by": event.added_by,
                "timestamp": event.timestamp.isoformat(),
            },
        )

    def on_participant_updated(self, event: ParticipantUpdatedEvent) -> None:
        """Обработка события обновления участника."""
        self.logger.info(
            f"✏️ Participant updated: {event.participant.full_name_ru}",
            extra={
                "event_type": "participant_updated",
                "participant_id": event.participant.id,
                "participant_name": event.participant.full_name_ru,
                "participant_role": event.participant.role,
                "updated_by": event.updated_by,
                "timestamp": event.timestamp.isoformat(),
            },
        )
