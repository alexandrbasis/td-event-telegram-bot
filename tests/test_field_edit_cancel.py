import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from main import handle_field_edit_cancel, CONFIRMING_DATA


class FieldEditCancelTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_cancel_returns_to_confirmation(self):
        query = MagicMock()
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        query.message = MagicMock()
        query.message.reply_text = AsyncMock()
        update = SimpleNamespace(callback_query=query,
                                 effective_user=SimpleNamespace(id=1))
        context = SimpleNamespace(user_data={'parsed_participant': {'Role': 'TEAM'}},
                                  bot=None)

        with patch('main.show_confirmation', new=AsyncMock()) as mock_show, \
             patch('main.get_edit_keyboard', return_value='kb'):
            state = await handle_field_edit_cancel(update, context)

        mock_show.assert_awaited_once()
        query.edit_message_text.assert_awaited_once()
        self.assertEqual(state, CONFIRMING_DATA)
        self.assertNotIn('field_to_edit', context.user_data)


if __name__ == '__main__':
    unittest.main()
