import re
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch


class TestSearchEditFlow(unittest.IsolatedAsyncioTestCase):
    async def test_edit_field_after_search_action_edit(self):
        # Structural assertion: global application-level handler for ^edit_ must exist
        # so that edit_* callbacks work when entering edit from search flow.
        with open("main.py", "r", encoding="utf-8") as f:
            src = f.read()

        pattern = re.compile(
            r"application\.add_handler\(\s*CallbackQueryHandler\(\s*edit_field_callback\s*,\s*pattern=\"\^edit_\"\s*\)\s*\)",
            re.MULTILINE,
        )
        self.assertRegex(
            src,
            pattern,
            msg="Global handler for ^edit_ must be registered so edit buttons work after search",
        )

        # Functional smoke: action_edit should prepare context and next edit_* should keep CONFIRMING_DATA
        from main import handle_action_selection, edit_field_callback, CONFIRMING_DATA
        from models.participant import Participant

        user_id = 1
        # Prepare context with a selected participant as done by search -> selection
        participant = Participant(
            FullNameRU="Иван Петров",
            Gender="M",
            Size="L",
            Church="Тест",
            Role="CANDIDATE",
        )
        participant.id = 123

        context = SimpleNamespace(user_data={"selected_participant": participant}, chat_data={})

        action_query = MagicMock()
        action_query.answer = AsyncMock()
        action_query.message = MagicMock()
        action_query.message.reply_text = AsyncMock()
        action_update = SimpleNamespace(callback_query=action_query, effective_user=SimpleNamespace(id=user_id))
        action_query.data = "action_edit"

        with patch("main.user_logger"), \
             patch("main.COORDINATOR_IDS", [user_id]), \
             patch("utils.decorators.COORDINATOR_IDS", [user_id]), \
             patch("main.show_confirmation", new=AsyncMock()):
            state = await handle_action_selection(action_update, context)

        self.assertEqual(state, CONFIRMING_DATA)
        self.assertEqual(context.user_data.get("participant_id"), 123)
        self.assertIn("parsed_participant", context.user_data)

        # Now simulate clicking an edit_* button
        edit_query = MagicMock()
        edit_query.answer = AsyncMock()
        edit_query.message = MagicMock()
        edit_query.message.reply_text = AsyncMock()
        edit_update = SimpleNamespace(callback_query=edit_query, effective_user=SimpleNamespace(id=user_id))
        edit_query.data = "edit_Role"

        with patch("main._add_message_to_cleanup", lambda *args, **kwargs: None), \
             patch("main.safe_create_timeout_job", return_value=None):
            next_state = await edit_field_callback(edit_update, context)

        self.assertEqual(next_state, CONFIRMING_DATA)
        self.assertEqual(context.user_data.get("field_to_edit"), "Role")

    async def test_cancel_edit_after_search_entry(self):
        from main import handle_action_selection, handle_field_edit_cancel, CONFIRMING_DATA
        from models.participant import Participant

        user_id = 2
        participant = Participant(
            FullNameRU="Мария Иванова",
            Gender="F",
            Size="M",
            Church="Тест",
            Role="CANDIDATE",
        )
        participant.id = 321

        context = SimpleNamespace(user_data={"selected_participant": participant}, chat_data={})

        action_query = MagicMock()
        action_query.answer = AsyncMock()
        action_query.message = MagicMock()
        action_query.message.reply_text = AsyncMock()
        action_update = SimpleNamespace(callback_query=action_query, effective_user=SimpleNamespace(id=user_id))
        action_query.data = "action_edit"

        with patch("main.user_logger"), \
             patch("main.COORDINATOR_IDS", [user_id]), \
             patch("utils.decorators.COORDINATOR_IDS", [user_id]), \
             patch("main.show_confirmation", new=AsyncMock()):
            state = await handle_action_selection(action_update, context)

        self.assertEqual(state, CONFIRMING_DATA)

        # Prepare edit state
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

    async def test_edit_field_without_context_shows_help(self):
        # Guard: when parsed_participant is missing, edit_* should show a hint and keep state
        from main import edit_field_callback, CONFIRMING_DATA

        user_id = 3
        context = SimpleNamespace(user_data={}, chat_data={})

        edit_query = MagicMock()
        edit_query.answer = AsyncMock()
        edit_query.message = MagicMock()
        edit_query.message.reply_text = AsyncMock()
        edit_update = SimpleNamespace(callback_query=edit_query, effective_user=SimpleNamespace(id=user_id))
        edit_query.data = "edit_Role"

        # _send_response_with_menu_button uses reply_text; no need to patch
        state = await edit_field_callback(edit_update, context)

        self.assertEqual(state, CONFIRMING_DATA)

    async def test_global_enum_handler_registered(self):
        # Structural assertion: global handler for enum selections must be registered
        import re
        with open("main.py", "r", encoding="utf-8") as f:
            src = f.read()
        pattern = re.compile(
            r"application\.add_handler\(\s*CallbackQueryHandler\(\s*handle_enum_selection\s*,\s*pattern=\"\^\(gender\|role\|size\|dept\)_\.\+\$\"\s*\)\s*\)",
            re.MULTILINE,
        )
        self.assertRegex(
            src,
            pattern,
            msg="Global handler for enum selections must be registered to work after search edit",
        )

    async def test_enum_selection_after_search_entry(self):
        # Functional: after starting edit via search, selecting enum (role_TEAM) should update data and stay in CONFIRMING_DATA
        from main import (
            handle_action_selection,
            handle_enum_selection,
            CONFIRMING_DATA,
        )
        from models.participant import Participant
        from types import SimpleNamespace
        from unittest.mock import AsyncMock, MagicMock, patch

        user_id = 4
        participant = Participant(
            FullNameRU="Тест Пользователь",
            Gender="M",
            Size="L",
            Church="Тест",
            Role="CANDIDATE",
        )
        participant.id = 555

        context = SimpleNamespace(user_data={"selected_participant": participant}, chat_data={})

        action_query = MagicMock()
        action_query.answer = AsyncMock()
        action_query.message = MagicMock()
        action_query.message.reply_text = AsyncMock()
        action_update = SimpleNamespace(callback_query=action_query, effective_user=SimpleNamespace(id=user_id))
        action_query.data = "action_edit"

        with patch("main.user_logger"), \
             patch("main.COORDINATOR_IDS", [user_id]), \
             patch("utils.decorators.COORDINATOR_IDS", [user_id]), \
             patch("main.show_confirmation", new=AsyncMock()):
            state = await handle_action_selection(action_update, context)

        self.assertEqual(state, CONFIRMING_DATA)
        # Simulate that user chose to edit Role and now clicks enum option role_TEAM
        context.user_data["field_to_edit"] = "Role"

        enum_query = MagicMock()
        enum_query.answer = AsyncMock()
        enum_query.message = MagicMock()
        enum_query.message.reply_text = AsyncMock()
        enum_update = SimpleNamespace(callback_query=enum_query, effective_user=SimpleNamespace(id=user_id))
        enum_query.data = "role_TEAM"

        with patch("main.show_confirmation", new=AsyncMock()):
            next_state = await handle_enum_selection(enum_update, context)

        self.assertEqual(next_state, CONFIRMING_DATA)
        self.assertEqual(context.user_data.get("parsed_participant", {}).get("Role"), "TEAM")
        # Department should be cleared when Role becomes TEAM
        self.assertEqual(context.user_data.get("parsed_participant", {}).get("Department", ""), "")

    async def test_text_input_after_search_edit_routes_to_confirmation(self):
        # After `action_edit` and setting field_to_edit, plain text must route to confirmation handler
        from main import (
            handle_action_selection,
            handle_participant_confirmation,
            handle_message,
            CONFIRMING_DATA,
        )
        from models.participant import Participant
        from types import SimpleNamespace
        from unittest.mock import AsyncMock, MagicMock, patch

        user_id = 5
        participant = Participant(
            FullNameRU="Старое Имя",
            Gender="M",
            Size="L",
            Church="Тест",
            Role="CANDIDATE",
        )
        participant.id = 777

        context = SimpleNamespace(user_data={"selected_participant": participant}, chat_data={})

        action_query = MagicMock()
        action_query.answer = AsyncMock()
        action_query.message = MagicMock()
        action_query.message.reply_text = AsyncMock()
        action_update = SimpleNamespace(callback_query=action_query, effective_user=SimpleNamespace(id=user_id))
        action_query.data = "action_edit"

        with patch("main.user_logger"), \
             patch("main.COORDINATOR_IDS", [user_id]), \
             patch("utils.decorators.COORDINATOR_IDS", [user_id]), \
             patch("main.show_confirmation", new=AsyncMock()):
            state = await handle_action_selection(action_update, context)

        self.assertEqual(state, CONFIRMING_DATA)

        # Prepare edit context and send text
        context.user_data["field_to_edit"] = "FullNameRU"
        text_update = SimpleNamespace(
            message=MagicMock(), effective_user=SimpleNamespace(id=user_id)
        )
        text_update.message.text = "Новое Имя"
        text_update.message.reply_text = AsyncMock()

        with patch("main.COORDINATOR_IDS", [user_id]), \
             patch("utils.decorators.COORDINATOR_IDS", [user_id]), \
             patch("main.show_confirmation", new=AsyncMock()) as mock_show:
            # Directly call participant_confirmation to ensure core logic works (authorized)
            next_state = await handle_participant_confirmation(text_update, context)
            self.assertEqual(next_state, CONFIRMING_DATA)
            mock_show.assert_awaited()

        # Also ensure handle_message delegates when field_to_edit is set
        context.user_data["field_to_edit"] = "FullNameRU"
        from main import ApplicationHandlerStop
        with patch("main.VIEWER_IDS", [user_id]), \
             patch("utils.decorators.VIEWER_IDS", [user_id]), \
             patch("main.handle_participant_confirmation", new=AsyncMock(return_value=CONFIRMING_DATA)) as mock_conf:
            with self.assertRaises(ApplicationHandlerStop):
                await handle_message(text_update, context)
            mock_conf.assert_awaited()

    async def test_confirm_save_after_search_entry(self):
        # After entering edit via search, pressing confirm_save should update and end
        from main import handle_action_selection, handle_save_confirmation, ConversationHandler
        from models.participant import Participant
        from types import SimpleNamespace
        from unittest.mock import AsyncMock, MagicMock, patch

        user_id = 6
        participant = Participant(
            FullNameRU="Имя",
            Gender="F",
            Size="M",
            Church="Тест",
            Role="CANDIDATE",
        )
        participant.id = 888

        context = SimpleNamespace(user_data={"selected_participant": participant}, chat_data={})

        action_query = MagicMock()
        action_query.answer = AsyncMock()
        action_query.message = MagicMock()
        action_query.message.reply_text = AsyncMock()
        action_update = SimpleNamespace(callback_query=action_query, effective_user=SimpleNamespace(id=user_id))
        action_query.data = "action_edit"

        with patch("main.user_logger"), \
             patch("main.COORDINATOR_IDS", [user_id]), \
             patch("utils.decorators.COORDINATOR_IDS", [user_id]), \
             patch("main.show_confirmation", new=AsyncMock()):
            await handle_action_selection(action_update, context)

        # Simulate pressing Save
        save_query = MagicMock()
        save_query.answer = AsyncMock()
        save_query.message = MagicMock()
        save_query.message.reply_text = AsyncMock()
        save_update = SimpleNamespace(callback_query=save_query, effective_user=SimpleNamespace(id=user_id), effective_chat=SimpleNamespace(id=1))
        save_query.data = "confirm_save"

        # Ensure parsed_participant is present
        context.user_data["parsed_participant"] = {
            "FullNameRU": "Имя",
            "Gender": "F",
            "Size": "M",
            "Church": "Тест",
            "Role": "CANDIDATE",
        }
        context.user_data["participant_id"] = participant.id

        import main as main_module
        fake_service = MagicMock()
        fake_service.update_participant = MagicMock()
        fake_service.get_participant = MagicMock(return_value=None)
        with patch("main.COORDINATOR_IDS", [user_id]), \
             patch("utils.decorators.COORDINATOR_IDS", [user_id]), \
             patch.object(main_module, "participant_service", fake_service), \
             patch("main._cleanup_messages", new=AsyncMock()), \
             patch("main.user_logger"):
            end_state = await handle_save_confirmation(save_update, context)

        fake_service.update_participant.assert_called_once()
        self.assertEqual(end_state, ConversationHandler.END)

    async def test_global_back_and_save_handlers_registered(self):
        # Structural asserts for global back/save handlers
        with open("main.py", "r", encoding="utf-8") as f:
            src = f.read()
        self.assertRegex(
            src,
            re.compile(r"application\.add_handler\(\s*CallbackQueryHandler\(\s*handle_field_edit_cancel\s*,\s*pattern=\"\^field_edit_cancel\$\"\s*\)\s*\)"),
            msg="Global handler for field_edit_cancel must be registered",
        )
        self.assertRegex(
            src,
            re.compile(r"application\.add_handler\(\s*CallbackQueryHandler\(\s*handle_save_confirmation\s*,\s*pattern=\"\^confirm_save\$\"\s*\)\s*\)"),
            msg="Global handler for confirm_save must be registered",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)


