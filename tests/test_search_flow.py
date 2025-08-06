import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from src.presentation.handlers.callback_handlers import SearchCallbackHandler
from main import cancel_callback, SEARCHING_PARTICIPANTS


class SearchFlowTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_search_after_cancel(self):
        context = SimpleNamespace(user_data={}, chat_data={})
        update = SimpleNamespace(
            callback_query=MagicMock(), effective_user=SimpleNamespace(id=1)
        )

        async def mock_show_search_prompt(update, context, is_callback=True):
            context.user_data["current_state"] = SEARCHING_PARTICIPANTS
            return SEARCHING_PARTICIPANTS

        ui_service = SimpleNamespace(
            show_search_prompt=AsyncMock(side_effect=mock_show_search_prompt)
        )

        with patch("main.user_logger"), patch(
            "main._cleanup_messages", new=AsyncMock()
        ), patch("main._show_main_menu", new=AsyncMock()), patch(
            "main._log_session_end"
        ), patch(
            "src.utils.decorators.VIEWER_IDS", [1]
        ), patch(
            "src.utils.decorators.COORDINATOR_IDS", []
        ):
            container = SimpleNamespace(
                logger=lambda: MagicMock(), user_logger=lambda: MagicMock()
            )
            search_use_case = AsyncMock()
            handler = SearchCallbackHandler(container, ui_service, search_use_case)
            state = await handler.handle(update, context)
            self.assertEqual(state, SEARCHING_PARTICIPANTS)
            self.assertIn("current_state", context.user_data)

            context.chat_data["conversation"] = "active"

            cancel_update = SimpleNamespace(
                callback_query=MagicMock(answer=AsyncMock()),
                effective_user=SimpleNamespace(id=1),
                effective_chat=SimpleNamespace(id=1),
            )

            await cancel_callback(cancel_update, context)

            self.assertEqual(context.user_data, {})
            self.assertEqual(context.chat_data, {})

            update2 = SimpleNamespace(
                callback_query=MagicMock(), effective_user=SimpleNamespace(id=1)
            )
            search_use_case2 = AsyncMock()
            handler2 = SearchCallbackHandler(container, ui_service, search_use_case2)
            state2 = await handler2.handle(update2, context)
            self.assertEqual(state2, SEARCHING_PARTICIPANTS)
            self.assertIn("current_state", context.user_data)


if __name__ == "__main__":
    unittest.main()
