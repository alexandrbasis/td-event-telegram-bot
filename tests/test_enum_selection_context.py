import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from main import handle_enum_selection, FILLING_MISSING_FIELDS, CONFIRMING_DATA


class EnumSelectionContextTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_continue_missing_fields(self):
        query = MagicMock()
        query.answer = AsyncMock()
        query.message = MagicMock()
        query.message.reply_text = AsyncMock()
        query.data = "gender_M"
        update = SimpleNamespace(
            callback_query=query, effective_user=SimpleNamespace(id=1)
        )
        context = SimpleNamespace(
            user_data={
                "add_flow_data": {"Gender": None, "Role": None},
                "current_state": CONFIRMING_DATA,
                "filling_missing_field": True,
            }
        )
        with patch(
            "main.show_interactive_missing_field", new=AsyncMock()
        ) as mock_show, patch("main.show_confirmation", new=AsyncMock()) as mock_conf:
            state = await handle_enum_selection(update, context)
        mock_show.assert_awaited_once()
        mock_conf.assert_not_awaited()
        self.assertEqual(state, FILLING_MISSING_FIELDS)
        self.assertEqual(context.user_data["add_flow_data"]["Gender"], "M")

    async def test_finish_missing_fields(self):
        query = MagicMock()
        query.answer = AsyncMock()
        query.message = MagicMock()
        query.message.reply_text = AsyncMock()
        query.data = "role_TEAM"
        update = SimpleNamespace(
            callback_query=query, effective_user=SimpleNamespace(id=1)
        )
        context = SimpleNamespace(
            user_data={
                "add_flow_data": {
                    "FullNameRU": "Test",
                    "Gender": "M",
                    "Size": "L",
                    "Church": "Grace",
                    "Role": None,
                    "Department": "Worship",
                },
                "current_state": CONFIRMING_DATA,
                "filling_missing_field": True,
            }
        )
        with patch(
            "main.show_interactive_missing_field", new=AsyncMock()
        ) as mock_show, patch("main.show_confirmation", new=AsyncMock()) as mock_conf:
            state = await handle_enum_selection(update, context)
        mock_show.assert_not_awaited()
        mock_conf.assert_awaited_once()
        self.assertEqual(state, CONFIRMING_DATA)
        self.assertFalse(context.user_data.get("filling_missing_field", True))

if __name__ == "__main__":
    unittest.main()
