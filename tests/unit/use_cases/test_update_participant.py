import pytest
from unittest.mock import AsyncMock, Mock

from src.application.use_cases.update_participant import (
    UpdateParticipantCommand,
    UpdateParticipantUseCase,
)
from src.models.participant import Participant
from src.shared.exceptions import DuplicateParticipantError


class TestUpdateParticipantUseCase:
    def setup_method(self):
        self.repository = AsyncMock()
        self.validator = Mock()
        self.duplicate_checker = AsyncMock()
        self.event_dispatcher = Mock()
        self.use_case = UpdateParticipantUseCase(
            self.repository,
            self.validator,
            self.duplicate_checker,
            self.event_dispatcher,
        )

    @pytest.mark.asyncio
    async def test_updates_participant_and_dispatches_event(self):
        existing = Participant.from_dict({"id": 1, "FullNameRU": "Old", "Gender": "M"})
        self.repository.find_by_id.return_value = existing
        self.validator.validate.return_value = Mock(is_valid=True)
        self.duplicate_checker.check_duplicate.return_value = None

        updated = Participant.from_dict({"id": 1, "FullNameRU": "New", "Gender": "M"})
        self.repository.save.return_value = updated

        command = UpdateParticipantCommand(
            participant_id=1,
            user_id=123,
            participant_data={"FullNameRU": "New"},
        )

        result = await self.use_case.execute(command)

        self.validator.validate.assert_called_once_with({"FullNameRU": "New"})
        self.duplicate_checker.check_duplicate.assert_called_once_with("New")
        self.repository.save.assert_called_once()
        self.event_dispatcher.dispatch.assert_called_once()
        assert result == updated

    @pytest.mark.asyncio
    async def test_raises_error_when_duplicate_found(self):
        existing = Participant.from_dict({"id": 1, "FullNameRU": "Old", "Gender": "M"})
        self.repository.find_by_id.return_value = existing
        self.validator.validate.return_value = Mock(is_valid=True)
        duplicate = Participant.from_dict({"id": 2, "FullNameRU": "New", "Gender": "M"})
        self.duplicate_checker.check_duplicate.return_value = duplicate

        command = UpdateParticipantCommand(
            participant_id=1,
            user_id=123,
            participant_data={"FullNameRU": "New"},
        )

        with pytest.raises(DuplicateParticipantError):
            await self.use_case.execute(command)

        self.repository.save.assert_not_called()
        self.event_dispatcher.dispatch.assert_not_called()
