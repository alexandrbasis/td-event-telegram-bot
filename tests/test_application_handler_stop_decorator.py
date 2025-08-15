import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from main import smart_cleanup_on_error, ApplicationHandlerStop, CONFIRMING_DATA


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

    async def test_errors_have_cancel_button_in_edit_context(self):
        # In edit context, validation errors should present a Cancel button
        # We'll simulate a handler that raises ValidationError under the decorator
        from utils.exceptions import ValidationError

        @smart_cleanup_on_error
        async def handler(update, context):
            raise ValidationError("Тестовая ошибка валидации")

        # Simulate being in edit confirmation
        context = SimpleNamespace(user_data={"current_state": CONFIRMING_DATA}, chat_data={})

        # Case 1: message-based
        update_msg = SimpleNamespace(
            message=MagicMock(),
            callback_query=None,
            effective_user=SimpleNamespace(id=2),
        )
        update_msg.message.reply_text = AsyncMock()
        _ = await handler(update_msg, context)
        args, kwargs = update_msg.message.reply_text.await_args
        kb = kwargs.get("reply_markup")
        self.assertIsNotNone(kb)
        # look for a button with text "❌ Отмена"
        cancel_found = any(
            any(getattr(btn, "text", "") == "❌ Отмена" for btn in row)
            for row in getattr(kb, "inline_keyboard", [])
        )
        self.assertTrue(cancel_found)

        # Case 2: callback-based
        update_cq = SimpleNamespace(
            message=None,
            callback_query=MagicMock(),
            effective_user=SimpleNamespace(id=3),
        )
        update_cq.callback_query.answer = AsyncMock()
        update_cq.callback_query.message = MagicMock()
        update_cq.callback_query.message.reply_text = AsyncMock()
        _ = await handler(update_cq, context)
        args, kwargs = update_cq.callback_query.message.reply_text.await_args
        kb = kwargs.get("reply_markup")
        self.assertIsNotNone(kb)
        cancel_found = any(
            any(getattr(btn, "text", "") == "❌ Отмена" for btn in row)
            for row in getattr(kb, "inline_keyboard", [])
        )
        self.assertTrue(cancel_found)


if __name__ == "__main__":
    unittest.main(verbosity=2)


