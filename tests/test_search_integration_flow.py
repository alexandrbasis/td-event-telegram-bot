import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from main import (
    handle_search_input,
    handle_participant_selection,
    ApplicationHandlerStop,
    SELECTING_PARTICIPANT,
    CHOOSING_ACTION,
)
from models.participant import Participant


class TestSearchIntegrationFlow(unittest.IsolatedAsyncioTestCase):
    async def test_search_results_then_select_participant_shows_details_and_actions(self):
        user_id = 123

        # Prepare update/context for search input
        update_msg = SimpleNamespace(
            effective_user=SimpleNamespace(id=user_id),
            message=MagicMock(),
            callback_query=None,
        )
        update_msg.message.text = "Иван"
        update_msg.message.reply_text = AsyncMock()
        update_msg.message.message_id = 100

        context = SimpleNamespace(user_data={}, chat_data={})

        # Fake participant and service
        participant = Participant(
            FullNameRU="Иван Петров",
            Gender="M",
            Size="L",
            Church="Благодать",
            Role="CANDIDATE",
        )

        class MockResult:
            def __init__(self, participant):
                self.participant = participant
                self.confidence = 1.0
                self.match_field = "FullNameRU"
                self.match_type = "exact"

        class FakeService:
            def search_participants(self, q, max_results=5):
                return [MockResult(participant)]

            def format_search_result(self, result):
                return f"{result.participant.FullNameRU} (ID: {result.participant.id or 1})"

        fake_service = FakeService()

        with patch("main.participant_service", fake_service), \
             patch("main._add_message_to_cleanup", lambda *args, **kwargs: None), \
             patch("main.user_logger"):
            # handle_search_input should raise ApplicationHandlerStop to block fallbacks
            with self.assertRaises(ApplicationHandlerStop):
                await handle_search_input(update_msg, context)

        # Simulate callback selection
        # Ensure IDs match parsing in handler
        selected_id = 1
        participant.id = selected_id
        context.user_data["search_results"] = [MockResult(participant)]

        update_cb = SimpleNamespace(
            effective_user=SimpleNamespace(id=user_id),
            message=None,
            callback_query=MagicMock(),
        )
        update_cb.callback_query.data = f"select_participant_{selected_id}"
        update_cb.callback_query.answer = AsyncMock()
        update_cb.callback_query.message = MagicMock()
        update_cb.callback_query.message.reply_text = AsyncMock()

        with patch("main.user_logger"):
            state = await handle_participant_selection(update_cb, context)
            self.assertEqual(state, CHOOSING_ACTION)
            # Details + actions were shown
            update_cb.callback_query.message.reply_text.assert_awaited()


if __name__ == "__main__":
    unittest.main(verbosity=2)


