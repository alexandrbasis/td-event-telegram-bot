import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from main import (
    recover_from_technical_error,
    smart_cleanup_on_error,
    CONFIRMING_DATA,
    RECOVERING,
    get_recovery_keyboard,
)


class RecoverTechnicalErrorTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_recover_function_returns_state(self):
        message = MagicMock()
        update = SimpleNamespace(message=message, callback_query=None, effective_user=SimpleNamespace(id=1))
        context = SimpleNamespace(user_data={"current_state": CONFIRMING_DATA})
        with patch("main.show_recovery_options", new=AsyncMock(return_value=RECOVERING)) as mock_show:
            state = await recover_from_technical_error(update, context)
        mock_show.assert_awaited_once()
        self.assertEqual(state, RECOVERING)

    async def test_decorator_handles_jobqueue_error(self):
        async def failing(update, context):
            raise AttributeError("job_queue missing")

        decorated = smart_cleanup_on_error(failing)

        update = SimpleNamespace(message=MagicMock(), callback_query=None, effective_user=SimpleNamespace(id=1))
        update.message.reply_text = AsyncMock()
        context = SimpleNamespace(user_data={"current_state": CONFIRMING_DATA})

        with patch("main.recover_from_technical_error", new=AsyncMock(return_value=RECOVERING)) as mock_recover:
            state = await decorated(update, context)

        mock_recover.assert_awaited_once()
        self.assertEqual(state, RECOVERING)
        self.assertIn("current_state", context.user_data)

    def test_recovery_keyboard_buttons(self):
        context = SimpleNamespace(user_data={"parsed_participant": {"Role": "TEAM"}, "add_flow_data": {"Size": "M"}})
        kb = get_recovery_keyboard(context)
        datas = [b.callback_data for row in kb.inline_keyboard for b in row]
        self.assertIn("recover_confirmation", datas)
        self.assertIn("recover_input", datas)
        self.assertIn("main_add", datas)
if __name__ == "__main__":
    unittest.main()
