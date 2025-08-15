import re
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch


class EditAfterAddFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_edit_button_enters_conversation(self):
        # Structural assertion: the edit callback must be registered as an entry_point of add_conv
        with open("main.py", "r", encoding="utf-8") as f:
            src = f.read()

        # Regex to ensure the pattern exists inside add_conv entry_points before states={
        pattern = re.compile(
            r"add_conv\s*=\s*ConversationHandler\s*\(\s*entry_points\s*=\s*\[(?:[\s\S]*?)CallbackQueryHandler\(\s*handle_edit_participant_callback\s*,\s*pattern=\"\^edit_participant_\"\s*\)(?:[\s\S]*?)\]\s*,\s*states\s*=\s*\{",
            re.MULTILINE,
        )
        self.assertRegex(
            src,
            pattern,
            msg="handle_edit_participant_callback must be wired as an entry_point of add_conv",
        )

        # Functional smoke: calling the handler should return CONFIRMING_DATA and set user_data
        from main import handle_edit_participant_callback, CONFIRMING_DATA
        from models.participant import Participant

        user_id = 1
        query = MagicMock()
        query.answer = AsyncMock()
        query.message = MagicMock()
        query.message.reply_text = AsyncMock()
        update = SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=user_id))
        context = SimpleNamespace(user_data={}, chat_data={})
        query.data = "edit_participant_123"

        participant = Participant(
            FullNameRU="Иван Петров",
            Gender="M",
            Size="L",
            Church="Тест",
            Role="CANDIDATE",
        )
        participant.id = 123

        # Patch the module-level participant_service object itself since tests import from main
        with patch("main.participant_service", new=SimpleNamespace(get_participant=lambda _id: participant)), \
             patch("main.user_logger"), \
             patch("main.show_confirmation", new=AsyncMock()), \
             patch("utils.decorators.COORDINATOR_IDS", [user_id]):
            state = await handle_edit_participant_callback(update, context)

        self.assertEqual(state, CONFIRMING_DATA)
        self.assertEqual(context.user_data.get("participant_id"), 123)
        self.assertIn("parsed_participant", context.user_data)

    async def test_edit_field_callback_triggers_after_entry(self):
        # Arrange: first, simulate entry via handle_edit_participant_callback
        from main import handle_edit_participant_callback, edit_field_callback, CONFIRMING_DATA
        from models.participant import Participant

        user_id = 1
        entry_query = MagicMock()
        entry_query.answer = AsyncMock()
        entry_query.message = MagicMock()
        entry_query.message.reply_text = AsyncMock()
        entry_update = SimpleNamespace(callback_query=entry_query, effective_user=SimpleNamespace(id=user_id))
        context = SimpleNamespace(user_data={}, chat_data={})
        entry_query.data = "edit_participant_123"

        participant = Participant(
            FullNameRU="Иван Петров",
            Gender="M",
            Size="L",
            Church="Тест",
            Role="CANDIDATE",
        )
        participant.id = 123

        with patch("main.participant_service", new=SimpleNamespace(get_participant=lambda _id: participant)), \
             patch("main.user_logger"), \
             patch("main.show_confirmation", new=AsyncMock()), \
             patch("utils.decorators.COORDINATOR_IDS", [user_id]):
            state = await handle_edit_participant_callback(entry_update, context)
        self.assertEqual(state, CONFIRMING_DATA)

        # Act: now simulate pressing an edit_* button
        edit_query = MagicMock()
        edit_query.answer = AsyncMock()
        edit_query.message = MagicMock()
        edit_query.message.reply_text = AsyncMock()
        edit_update = SimpleNamespace(callback_query=edit_query, effective_user=SimpleNamespace(id=user_id))
        edit_query.data = "edit_FullNameRU"

        with patch("main._add_message_to_cleanup", lambda *args, **kwargs: None), \
             patch("main.safe_create_timeout_job", return_value=None):
            next_state = await edit_field_callback(edit_update, context)

        self.assertEqual(next_state, CONFIRMING_DATA)
        self.assertEqual(context.user_data.get("field_to_edit"), "FullNameRU")

    def test_no_global_handler_conflict(self):
        # There must be no global application-level handler for ^edit_participant_
        with open("main.py", "r", encoding="utf-8") as f:
            src = f.read()

        # Ensure there is no global registration like:
        # application.add_handler(CallbackQueryHandler(handle_edit_participant_callback, pattern="^edit_participant_") )
        self.assertNotIn(
            "application.add_handler(\n        CallbackQueryHandler(\n            handle_edit_participant_callback, pattern=\"^edit_participant_\"\n        )\n    )",
            src,
            msg="Global handler for ^edit_participant_ must not be registered; it should be only an entry_point of add_conv",
        )

    async def test_enum_selection_after_entry_clears_field_and_updates_data(self):
        # Arrange: enter via edit button
        from main import handle_edit_participant_callback, handle_enum_selection, CONFIRMING_DATA
        from models.participant import Participant

        user_id = 1
        entry_query = MagicMock()
        entry_query.answer = AsyncMock()
        entry_query.message = MagicMock()
        entry_query.message.reply_text = AsyncMock()
        entry_update = SimpleNamespace(callback_query=entry_query, effective_user=SimpleNamespace(id=user_id))
        context = SimpleNamespace(user_data={}, chat_data={})
        entry_query.data = "edit_participant_123"

        participant = Participant(
            FullNameRU="Иван Петров",
            Gender="M",
            Size="L",
            Church="Тест",
            Role="CANDIDATE",
        )
        participant.id = 123

        with patch("main.participant_service", new=SimpleNamespace(get_participant=lambda _id: participant)), \
             patch("main.user_logger"), \
             patch("main.show_confirmation", new=AsyncMock()), \
             patch("utils.decorators.COORDINATOR_IDS", [user_id]):
            state = await handle_edit_participant_callback(entry_update, context)
        self.assertEqual(state, CONFIRMING_DATA)

        # Simulate that user chose to edit Role and then selected TEAM
        context.user_data["field_to_edit"] = "Role"
        context.user_data["clear_edit_job"] = SimpleNamespace(schedule_removal=lambda: None)

        enum_query = MagicMock()
        enum_query.answer = AsyncMock()
        enum_query.message = MagicMock()
        enum_query.message.reply_text = AsyncMock()
        enum_update = SimpleNamespace(callback_query=enum_query, effective_user=SimpleNamespace(id=user_id))
        enum_query.data = "role_TEAM"

        with patch("main.get_department_selection_keyboard_required", return_value="DEPT_KB") as kb_mock, \
             patch("main.show_confirmation", new=AsyncMock()) as mock_show:
            next_state = await handle_enum_selection(enum_update, context)

        self.assertEqual(next_state, CONFIRMING_DATA)
        # field_to_edit must be cleared
        self.assertNotIn("field_to_edit", context.user_data)
        # parsed_participant should be updated to TEAM and Department cleared
        parsed = context.user_data.get("parsed_participant", {})
        self.assertEqual(parsed.get("Role"), "TEAM")
        # Department may be set to empty string when switching to/from TEAM
        self.assertIn("Department", parsed)
        # Now we expect immediate department prompt instead of confirmation
        mock_show.assert_not_awaited()
        enum_query.message.reply_text.assert_awaited()
        args, kwargs = enum_query.message.reply_text.await_args
        self.assertIn("reply_markup", kwargs)
        self.assertEqual(kwargs.get("reply_markup"), "DEPT_KB")

    async def test_cancel_edit_returns_confirmation_and_clears_timeout(self):
        from main import handle_edit_participant_callback, handle_field_edit_cancel, CONFIRMING_DATA
        from models.participant import Participant

        user_id = 1
        entry_query = MagicMock()
        entry_query.answer = AsyncMock()
        entry_query.message = MagicMock()
        entry_query.message.reply_text = AsyncMock()
        entry_update = SimpleNamespace(callback_query=entry_query, effective_user=SimpleNamespace(id=user_id))
        context = SimpleNamespace(user_data={}, chat_data={})
        entry_query.data = "edit_participant_123"

        participant = Participant(
            FullNameRU="Иван Петров",
            Gender="M",
            Size="L",
            Church="Тест",
            Role="CANDIDATE",
        )
        participant.id = 123

        with patch("main.participant_service", new=SimpleNamespace(get_participant=lambda _id: participant)), \
             patch("main.user_logger"), \
             patch("main.show_confirmation", new=AsyncMock()), \
             patch("utils.decorators.COORDINATOR_IDS", [user_id]):
            state = await handle_edit_participant_callback(entry_update, context)
        self.assertEqual(state, CONFIRMING_DATA)

        # Prepare state for cancel: field_to_edit and clear_edit_job present
        context.user_data["field_to_edit"] = "FullNameRU"
        context.user_data["clear_edit_job"] = SimpleNamespace(schedule_removal=lambda: None)

        cancel_query = MagicMock()
        cancel_query.answer = AsyncMock()
        cancel_query.edit_message_text = AsyncMock()
        cancel_query.message = MagicMock()
        cancel_query.message.reply_text = AsyncMock()
        cancel_update = SimpleNamespace(callback_query=cancel_query, effective_user=SimpleNamespace(id=user_id))

        with patch("main.show_confirmation", new=AsyncMock()) as mock_show, \
             patch("main.get_edit_keyboard", return_value="kb"):
            next_state = await handle_field_edit_cancel(cancel_update, context)

        self.assertEqual(next_state, CONFIRMING_DATA)
        self.assertNotIn("field_to_edit", context.user_data)
        self.assertNotIn("clear_edit_job", context.user_data)
        mock_show.assert_awaited_once()
        cancel_query.edit_message_text.assert_awaited_once()

    async def test_confirm_save_after_edit_entry(self):
        # Ensure pressing Save after entering via edit entry works
        from main import handle_edit_participant_callback, handle_save_confirmation
        from telegram.ext import ConversationHandler
        from models.participant import Participant

        user_id = 1
        # Enter via edit button
        entry_query = MagicMock()
        entry_query.answer = AsyncMock()
        entry_query.message = MagicMock()
        entry_query.message.reply_text = AsyncMock()
        entry_update = SimpleNamespace(
            callback_query=entry_query,
            effective_user=SimpleNamespace(id=user_id),
            effective_chat=SimpleNamespace(id=100),
        )
        context = SimpleNamespace(user_data={}, chat_data={})
        entry_query.data = "edit_participant_123"

        participant = Participant(
            FullNameRU="Иван Петров",
            Gender="M",
            Size="L",
            Church="Тест",
            Role="CANDIDATE",
        )
        participant.id = 123

        with patch("main.participant_service", new=SimpleNamespace(get_participant=lambda _id: participant)), \
             patch("main.user_logger"), \
             patch("main.show_confirmation", new=AsyncMock()), \
             patch("utils.decorators.COORDINATOR_IDS", [user_id]):
            _ = await handle_edit_participant_callback(entry_update, context)

        # Now simulate pressing Save
        save_query = MagicMock()
        save_query.answer = AsyncMock()
        save_query.message = MagicMock()
        save_query.message.reply_text = AsyncMock()
        save_update = SimpleNamespace(
            callback_query=save_query,
            effective_user=SimpleNamespace(id=user_id),
            effective_chat=SimpleNamespace(id=100),
        )
        save_query.data = "confirm_save"

        # Mock service to update and return updated participant for full-info formatting
        def _update_participant(_id, data, user_id=None):
            return True

        with patch("main.participant_service", new=SimpleNamespace(
            update_participant=_update_participant,
            get_participant=lambda _id: participant,
            check_duplicate=lambda *args, **kwargs: None,
        )), \
             patch("main._cleanup_messages", new=AsyncMock()), \
             patch("main.user_logger"), \
             patch("utils.decorators.COORDINATOR_IDS", [user_id]):
            state = await handle_save_confirmation(save_update, context)

        self.assertEqual(state, ConversationHandler.END)
        save_query.message.reply_text.assert_awaited()


if __name__ == "__main__":
    unittest.main(verbosity=2)


