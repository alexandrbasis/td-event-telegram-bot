import unittest
import sqlite3

from src.database import (
    get_participant_by_id,
    find_participant_by_name,
    init_database,
)
from src.repositories.participant_repository import SqliteParticipantRepository

import src.database as database

database.DB_PATH = ":memory:"


class MissingLookupReturnsNoneTestCase(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(database.DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self._original_enter = database.DatabaseConnection.__enter__
        self._original_exit = database.DatabaseConnection.__exit__

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

    def tearDown(self):
        database.DatabaseConnection.__enter__ = self._original_enter
        database.DatabaseConnection.__exit__ = self._original_exit
        self.conn.close()

    def test_get_participant_by_id_none(self):
        result = get_participant_by_id(99999)
        print(f"get_participant_by_id(99999): {result}")
        self.assertIsNone(result)

    def test_find_participant_by_name_none(self):
        result = find_participant_by_name("Несуществующий Участник")
        print(f"find_participant_by_name: {result}")
        self.assertIsNone(result)

    def test_repository_get_by_id_none(self):
        repo = SqliteParticipantRepository()
        result = repo.get_by_id(99999)
        print(f"repo.get_by_id(99999): {result}")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
