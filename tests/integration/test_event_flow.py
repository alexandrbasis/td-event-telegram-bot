from datetime import datetime
from unittest.mock import AsyncMock, Mock
import asyncio

from src.application.use_cases.add_participant import (
    AddParticipantUseCase,
    AddParticipantCommand,
)
from src.application.event_handlers.participant_event_listener import (
    ParticipantEventListener,
)
from src.shared.event_dispatcher import EventDispatcher
from src.domain.events.participant_events import ParticipantAddedEvent


class TestEventFlow:
    """Интеграционные тесты полного потока событий."""

    def setup_method(self):
        self.repository = AsyncMock()
        self.validator = Mock()
        self.duplicate_checker = AsyncMock()
        self.dispatcher = EventDispatcher()
        self.logger = Mock()

        # Настройка listener
        self.listener = ParticipantEventListener(self.logger)
        self.dispatcher.subscribe(
            ParticipantAddedEvent, self.listener.on_participant_added
        )

        # Создание use case
        self.use_case = AddParticipantUseCase(
            self.repository,
            self.validator,
            self.duplicate_checker,
            self.dispatcher,
        )

    def test_complete_event_flow(self):
        """Тест полного потока: Use Case -> Event -> Listener."""
        # Настройка mocks
        self.validator.validate.return_value = Mock(is_valid=True)
        self.duplicate_checker.check_duplicate.return_value = None

        from src.domain.models.participant import Participant

        participant = Participant.from_dict({"FullNameRU": "Test", "Gender": "M"})
        participant.id = 1
        self.repository.save.return_value = participant

        # Выполнение команды
        command = AddParticipantCommand(
            user_id=123, participant_data={"FullNameRU": "Test", "Gender": "M"}
        )

        result = asyncio.run(self.use_case.execute(command))

        # Проверки
        assert result is not None
        assert result.full_name_ru == "Test"

        # Проверяем что событие было обработано
        self.logger.info.assert_called_once()
        args, kwargs = self.logger.info.call_args
        assert "Test" in args[0]
        assert kwargs["extra"]["event_type"] == "participant_added"
