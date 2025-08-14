import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from main import smart_cleanup_on_error, ApplicationHandlerStop


class TestApplicationHandlerStopDecorator(unittest.IsolatedAsyncioTestCase):
    async def test_decorator_propagates_application_handler_stop(self):
        async def raises_stop(update, context):
            # Simulate ConversationHandler stop with state payload
            raise ApplicationHandlerStop(8)

        decorated = smart_cleanup_on_error(raises_stop)

        update = SimpleNamespace(
            message=MagicMock(),
            callback_query=None,
            effective_user=SimpleNamespace(id=1),
        )
        update.message.reply_text = AsyncMock()
        context = SimpleNamespace(user_data={}, chat_data={})

        with self.assertRaises(ApplicationHandlerStop):
            await decorated(update, context)


if __name__ == "__main__":
    unittest.main(verbosity=2)


