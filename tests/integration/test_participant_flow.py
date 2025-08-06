from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from tests.fixtures.container import create_test_container
from src.application.controllers.participant_controller import MAIN_MENU
from src.states import COLLECTING_DATA


class TestCompleteParticipantFlow:
    def setup_method(self):
        self.container = create_test_container()
        self.controller = self.container.participant_controller()

    @pytest.mark.asyncio
    async def test_add_participant_complete_flow(self):
        update = SimpleNamespace(
            effective_user=SimpleNamespace(id=123),
            message=AsyncMock(),
        )
        context = SimpleNamespace(user_data={})

        state = await self.controller.start_add_flow(update, context)
        assert state == COLLECTING_DATA

        participant_data = {"FullNameRU": "Test User", "Gender": "M"}
        update.message.reply_text.reset_mock()
        state = await self.controller.handle_add_data(update, context, participant_data)
        assert state == MAIN_MENU

        participants = await self.container.list_participants_use_case().execute()
        assert len(participants) == 1
