import unittest
import sqlite3

import database
from database import init_database
from repositories.participant_repository import SqliteParticipantRepository
from services.participant_service import ParticipantService

# use in-memory database
database.DB_PATH = ":memory:"


class ParticipantServiceTestCase(unittest.TestCase):
    def setUp(self):
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

    def test_add_participant_returns_object(self):
        data = {
            "FullNameRU": "Тестовый Пользователь",
            "Gender": "M",
            "Size": "L",
            "Church": "Тест",
            "Role": "CANDIDATE",
        }
        participant = self.service.add_participant(data)
        self.assertIsNotNone(participant.id)
        self.assertEqual(participant.FullNameRU, "Тестовый Пользователь")


if __name__ == "__main__":
    unittest.main()
