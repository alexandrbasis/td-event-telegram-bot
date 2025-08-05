import sys
from pathlib import Path

import pytest
from unittest.mock import AsyncMock, Mock

sys.path.append(str(Path(__file__).resolve().parents[3] / "src"))

from application.use_cases.add_participant import (
    AddParticipantCommand,
    AddParticipantUseCase,
)
from domain.models.participant import Participant


class TestAddParticipantUseCase:
    def setup_method(self):
        self.repository = AsyncMock()
        self.validator = Mock()
        self.duplicate_checker = AsyncMock()
        self.event_dispatcher = Mock()
        self.use_case = AddParticipantUseCase(
            self.repository,
            self.validator,
            self.duplicate_checker,
            self.event_dispatcher,
        )

    @pytest.mark.asyncio
    async def test_adds_valid_participant(self):
        participant_data = {"FullNameRU": "Test", "Gender": "M"}
        command = AddParticipantCommand(user_id=1, participant_data=participant_data)

        self.validator.validate.return_value = Mock(is_valid=True)
        self.duplicate_checker.check_duplicate.return_value = None
        saved_participant = Participant.from_dict(participant_data)
        self.repository.save.return_value = saved_participant

        result = await self.use_case.execute(command)

        self.validator.validate.assert_called_once_with(participant_data)
        self.duplicate_checker.check_duplicate.assert_called_once()
        self.repository.save.assert_called_once()
        self.event_dispatcher.dispatch.assert_called_once()
        assert result == saved_participant
