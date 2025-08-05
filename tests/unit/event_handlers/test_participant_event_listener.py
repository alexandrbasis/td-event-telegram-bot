import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock

import pytest

sys.path.append(str(Path(__file__).resolve().parents[3] / "src"))

from application.event_handlers.participant_event_listener import (
    ParticipantEventListener,
)
from domain.events.participant_events import (
    ParticipantAddedEvent,
    ParticipantUpdatedEvent,
)
from domain.models.participant import Participant


class TestParticipantEventListener:
    def setup_method(self):
        self.logger = Mock()
        self.listener = ParticipantEventListener(self.logger)

    def test_logs_participant_added_event(self):
        """Тест логирования события добавления участника."""
        participant = Participant.from_dict(
            {"id": 1, "FullNameRU": "Test User", "Gender": "M", "role": "CANDIDATE"}
        )

        event = ParticipantAddedEvent(
            participant=participant,
            added_by=123,
            timestamp=datetime(2025, 1, 1, 12, 0, 0),
        )

        self.listener.on_participant_added(event)

        # Проверяем что логирование было вызвано с правильными параметрами
        self.logger.info.assert_called_once()
        args, kwargs = self.logger.info.call_args

        assert "Test User" in args[0]
        assert "event_type" in kwargs["extra"]
        assert kwargs["extra"]["event_type"] == "participant_added"
        assert kwargs["extra"]["participant_name"] == "Test User"

    def test_logs_participant_updated_event(self):
        """Тест логирования события обновления участника."""
        participant = Participant.from_dict(
            {"id": 1, "FullNameRU": "Updated User", "Gender": "F", "role": "TEAM"}
        )

        event = ParticipantUpdatedEvent(
            participant=participant,
            updated_by=456,
            timestamp=datetime(2025, 1, 1, 12, 0, 0),
        )

        self.listener.on_participant_updated(event)

        # Проверяем логирование
        self.logger.info.assert_called_once()
        args, kwargs = self.logger.info.call_args

        assert "Updated User" in args[0]
        assert kwargs["extra"]["event_type"] == "participant_updated"
        assert kwargs["extra"]["updated_by"] == 456
