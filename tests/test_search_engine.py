import unittest
import sqlite3

import database
from database import init_database
from repositories.participant_repository import SqliteParticipantRepository
from services.participant_service import ParticipantService

# use in-memory database

database.DB_PATH = ":memory:"


class SearchEngineTestCase(unittest.TestCase):
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

        # Base participants
        self.p1 = self.service.add_participant(
            {
                "FullNameRU": "Иван Петров",
                "FullNameEN": "Ivan Petrov",
                "Gender": "M",
                "Size": "L",
                "Church": "Благодать",
                "Role": "CANDIDATE",
            }
        )
        self.p2 = self.service.add_participant(
            {
                "FullNameRU": "Анна Иванова",
                "FullNameEN": "Anna Ivanova",
                "Gender": "F",
                "Size": "M",
                "Church": "Грейс",
                "Role": "CANDIDATE",
            }
        )

        # Extra participants for max_results test
        for i in range(6):
            self.service.add_participant(
                {
                    "FullNameRU": f"Иван {i}",
                    "Gender": "M",
                    "Size": "L",
                    "Church": "Test",
                    "Role": "CANDIDATE",
                }
            )

    def tearDown(self):
        database.DatabaseConnection.__enter__ = self._orig_enter
        database.DatabaseConnection.__exit__ = self._orig_exit
        self.conn.close()

    def test_search_by_id(self):
        results = self.service.search_participants(str(self.p1.id))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].participant.id, self.p1.id)
        self.assertEqual(results[0].match_field, "id")

    def test_search_by_russian_name(self):
        results = self.service.search_participants("Иван Петров")
        self.assertTrue(any(r.participant.id == self.p1.id for r in results))
        self.assertEqual(results[0].confidence, 1.0)

    def test_search_by_english_name(self):
        results = self.service.search_participants("Ivan Petrov")
        self.assertEqual(results[0].participant.id, self.p1.id)
        self.assertEqual(results[0].match_field, "name_en")

    def test_fuzzy_search_confidence(self):
        results = self.service.search_participants("Ива")
        self.assertTrue(results)
        self.assertGreaterEqual(results[0].confidence, 0.6)

    def test_max_results_limit(self):
        results = self.service.search_participants("Иван")
        self.assertLessEqual(len(results), 5)

    def test_search_result_formatting(self):
        result = self.service.search_participants(str(self.p1.id))[0]
        formatted = self.service.format_search_result(result)
        self.assertIn("Иван Петров", formatted)
        self.assertIn(f"ID: {self.p1.id}", formatted)


if __name__ == "__main__":
    unittest.main()
