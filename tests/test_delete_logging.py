import unittest
import sqlite3
import json

import database
from database import init_database
from repositories.participant_repository import SqliteParticipantRepository
from services.participant_service import ParticipantService


class TestDeleteLogging(unittest.TestCase):
    def setUp(self):
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
        database.DatabaseConnection.__enter__ = self._orig_enter
        database.DatabaseConnection.__exit__ = self._orig_exit
        self.conn.close()

    def test_delete_logs_reason_and_participant_id(self):
        p = self.service.add_participant(
            {
                "FullNameRU": "Тест Удаление",
                "Gender": "M",
                "Size": "L",
                "Church": "Тест",
                "Role": "CANDIDATE",
            },
            user_id=42,
        )

        with self.assertLogs("participant_changes", level="INFO") as cm:
            self.service.delete_participant(p.id, user_id=42, reason="unit-test")

        self.assertTrue(cm.output, "No logs captured for participant_changes")

        # Find the delete log entry
        delete_logs = [line for line in cm.output if '"operation": "delete"' in line]
        self.assertTrue(delete_logs, "No delete operation log found")

        # Parse JSON payload from the log line
        # assertLogs uses format: LEVEL:LOGGER:MESSAGE
        payload = delete_logs[-1].split(":", 2)[2]
        entry = json.loads(payload)

        self.assertEqual(entry.get("operation"), "delete")
        self.assertEqual(entry.get("participant_id"), p.id)
        self.assertEqual(entry.get("data", {}).get("reason"), "unit-test")


if __name__ == "__main__":
    unittest.main(verbosity=2)


