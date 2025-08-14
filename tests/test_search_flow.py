import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from main import handle_search_callback, cancel_callback, SEARCHING_PARTICIPANTS


class SearchFlowTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_search_after_cancel(self):
        context = SimpleNamespace(user_data={}, chat_data={})
        update = SimpleNamespace(
            callback_query=MagicMock(), effective_user=SimpleNamespace(id=1)
        )

        async def mock_show_search_prompt(update, context, is_callback=True):
            context.user_data["current_state"] = SEARCHING_PARTICIPANTS
            return SEARCHING_PARTICIPANTS

        with patch(
            "main._show_search_prompt", side_effect=mock_show_search_prompt
        ), patch("main.user_logger"), patch(
            "main._cleanup_messages", new=AsyncMock()
        ), patch(
            "main._show_main_menu", new=AsyncMock()
        ), patch(
            "main._log_session_end"
        ), patch(
            "utils.decorators.VIEWER_IDS", [1]
        ), patch(
            "utils.decorators.COORDINATOR_IDS", []
        ):
            state = await handle_search_callback(update, context)
            self.assertEqual(state, SEARCHING_PARTICIPANTS)
            self.assertIn("current_state", context.user_data)

    async def test_new_search_works_from_selecting_participant(self):
        context = SimpleNamespace(
            user_data={
                "search_results": [1, 2, 3],
                "selected_participant": {"id": 123},
                "payment_participant": {"id": 999},
                "payment_amount": 150,
                "current_state": 8,  # SELECTING_PARTICIPANT
            },
            chat_data={},
        )

        update = SimpleNamespace(
            callback_query=MagicMock(),
            effective_user=SimpleNamespace(id=1),
        )
        update.callback_query.answer = AsyncMock()

        async def mock_show_search_prompt(update, context, is_callback=True):
            context.user_data["current_state"] = SEARCHING_PARTICIPANTS
            return SEARCHING_PARTICIPANTS

        with patch(
            "main._show_search_prompt", side_effect=mock_show_search_prompt
        ), patch("main.user_logger"), patch(
            "utils.decorators.VIEWER_IDS", [1]
        ), patch(
            "utils.decorators.COORDINATOR_IDS", []
        ):
            state = await handle_search_callback(update, context)

        self.assertEqual(state, SEARCHING_PARTICIPANTS)
        # Relevant keys must be cleaned
        for key in [
            "search_results",
            "selected_participant",
            "payment_participant",
            "payment_amount",
        ]:
            self.assertNotIn(key, context.user_data)
        self.assertIn("current_state", context.user_data)

    async def test_new_search_works_from_choosing_action(self):
        context = SimpleNamespace(
            user_data={
                "selected_participant": {"id": 123},
                "payment_participant": {"id": 999},
                "payment_amount": 150,
                "current_state": 9,  # CHOOSING_ACTION
            },
            chat_data={},
        )

        update = SimpleNamespace(
            callback_query=MagicMock(),
            effective_user=SimpleNamespace(id=1),
        )
        update.callback_query.answer = AsyncMock()

        async def mock_show_search_prompt(update, context, is_callback=True):
            context.user_data["current_state"] = SEARCHING_PARTICIPANTS
            return SEARCHING_PARTICIPANTS

        with patch(
            "main._show_search_prompt", side_effect=mock_show_search_prompt
        ), patch("main.user_logger"), patch(
            "utils.decorators.VIEWER_IDS", [1]
        ), patch(
            "utils.decorators.COORDINATOR_IDS", []
        ):
            state = await handle_search_callback(update, context)

        self.assertEqual(state, SEARCHING_PARTICIPANTS)
        for key in [
            "search_results",
            "selected_participant",
            "payment_participant",
            "payment_amount",
        ]:
            self.assertNotIn(key, context.user_data)
        self.assertIn("current_state", context.user_data)


class TestSearchExcludesDeletedParticipant(unittest.TestCase):
    def setUp(self):
        import sqlite3
        import database
        from database import init_database
        from repositories.participant_repository import SqliteParticipantRepository
        from services.participant_service import ParticipantService

        # Use a shared in-memory DB and patch DatabaseConnection
        database.DB_PATH = ":memory:"
        self.conn = sqlite3.connect(database.DB_PATH)
        self.conn.row_factory = sqlite3.Row

        self._orig_enter = database.DatabaseConnection.__enter__
        self._orig_exit = database.DatabaseConnection.__exit__

        def _enter(_self):
            _self.conn = self.conn
            return self.conn

        def _exit(_self, exc_type, exc_val, exc_tb):
            if exc_type:
                self.conn.rollback()
            else:
                self.conn.commit()

        database.DatabaseConnection.__enter__ = _enter
        database.DatabaseConnection.__exit__ = _exit

        init_database()
        self.service = ParticipantService(SqliteParticipantRepository())

    def tearDown(self):
        import database
        database.DatabaseConnection.__enter__ = self._orig_enter
        database.DatabaseConnection.__exit__ = self._orig_exit
        self.conn.close()

    def test_search_excludes_deleted_participant(self):
        # Arrange: add a participant
        data = {
            "FullNameRU": "Иван Петров",
            "Gender": "M",
            "Size": "L",
            "Church": "Тест",
            "Role": "CANDIDATE",
        }
        participant = self.service.add_participant(data, user_id=1)
        self.assertIsNotNone(participant.id)

        # Prime cache by searching (fuzzy query should find the participant)
        results_before = self.service.search_participants("Иван")
        self.assertTrue(any(r.participant.id == participant.id for r in results_before))

        # Act: delete participant
        self.service.delete_participant(participant.id, user_id=1, reason="test")

        # Assert: subsequent searches should not return the deleted participant
        results_after_fuzzy = self.service.search_participants("Иван")
        self.assertFalse(any(r.participant.id == participant.id for r in results_after_fuzzy))

        results_after_exact = self.service.search_participants("Иван Петров")
        self.assertFalse(any(r.participant.id == participant.id for r in results_after_exact))


class TestCacheUpdateOnMutations(unittest.TestCase):
    def setUp(self):
        import sqlite3
        import database
        from database import init_database
        from repositories.participant_repository import SqliteParticipantRepository
        from services.participant_service import ParticipantService

        database.DB_PATH = ":memory:"
        self.conn = sqlite3.connect(database.DB_PATH)
        self.conn.row_factory = sqlite3.Row

        self._orig_enter = database.DatabaseConnection.__enter__
        self._orig_exit = database.DatabaseConnection.__exit__

        def _enter(_self):
            _self.conn = self.conn
            return self.conn

        def _exit(_self, exc_type, exc_val, exc_tb):
            if exc_type:
                self.conn.rollback()
            else:
                self.conn.commit()

        database.DatabaseConnection.__enter__ = _enter
        database.DatabaseConnection.__exit__ = _exit

        init_database()
        self.service = ParticipantService(SqliteParticipantRepository())

    def tearDown(self):
        import database
        database.DatabaseConnection.__enter__ = self._orig_enter
        database.DatabaseConnection.__exit__ = self._orig_exit
        self.conn.close()

    def test_search_includes_new_participant_immediately(self):
        # Prime cache with empty list
        self.assertEqual(self.service.search_participants("Мария"), [])

        # Add participant
        participant = self.service.add_participant(
            {
                "FullNameRU": "Мария Иванова",
                "Gender": "F",
                "Size": "M",
                "Church": "Тест",
                "Role": "CANDIDATE",
            },
            user_id=1,
        )
        self.assertIsNotNone(participant.id)

        # Must be visible immediately in search
        results = self.service.search_participants("Мария Иванова")
        self.assertTrue(any(r.participant.id == participant.id for r in results))

    def test_search_reflects_updates_immediately(self):
        # Add and prime cache
        p = self.service.add_participant(
            {
                "FullNameRU": "Иван Петров",
                "Gender": "M",
                "Size": "L",
                "Church": "Тест",
                "Role": "CANDIDATE",
            },
            user_id=1,
        )
        _ = self.service.search_participants("Иван Петров")

        # Update name
        self.service.update_participant_fields(p.id, user_id=1, FullNameRU="Иван Сидоров")

        # New name should be found immediately
        new_results = self.service.search_participants("Иван Сидоров")
        self.assertTrue(any(r.participant.id == p.id for r in new_results))

    def test_search_reflects_payment_changes_immediately(self):
        # Add and prime cache
        p = self.service.add_participant(
            {
                "FullNameRU": "Павел Смирнов",
                "Gender": "M",
                "Size": "L",
                "Church": "Тест",
                "Role": "CANDIDATE",
            },
            user_id=1,
        )
        _ = self.service.search_participants("Павел Смирнов")

        # Process payment
        self.service.process_payment(p.id, amount=150, user_id=1)

        # Search should reflect updated payment fields immediately
        results = self.service.search_participants("Павел Смирнов")
        target = next((r for r in results if r.participant.id == p.id), None)
        self.assertIsNotNone(target)
        self.assertEqual(target.participant.PaymentStatus, "Paid")
        self.assertEqual(target.participant.PaymentAmount, 150)
        self.assertTrue(bool(target.participant.PaymentDate))


class TestSearchHandlerWiring(unittest.TestCase):
    def test_main_search_patterns_present_in_states(self):
        # Lightweight structural check that ConversationHandler states wire main_search
        with open("main.py", "r", encoding="utf-8") as f:
            src = f.read()

        # SELECTING_PARTICIPANT section contains main_search handler
        self.assertIn("SELECTING_PARTICIPANT", src)
        self.assertIn("handle_search_callback, pattern=\"^main_search$\"", src)

        # CHOOSING_ACTION section contains main_search handler
        self.assertIn("CHOOSING_ACTION", src)
        self.assertIn("handle_search_callback, pattern=\"^main_search$\"", src)

if __name__ == "__main__":
    unittest.main()
