import unittest
import sqlite3
import asyncio

import database
from database import init_database, get_participant_by_id
from repositories.participant_repository import SqliteParticipantRepository
from services.participant_service import ParticipantService


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
        repo = SqliteParticipantRepository()
        self.service = ParticipantService(repository=repo)

    def tearDown(self):
        database.DatabaseConnection.__enter__ = self._orig_enter
        database.DatabaseConnection.__exit__ = self._orig_exit
        self.conn.close()

    def test_candidate_department_cleared_on_add(self):
        data = {
            'FullNameRU': 'User A',
            'Gender': 'M',
            'Size': 'L',
            'Church': 'Test',
            'Role': 'CANDIDATE',
            'Department': 'Worship',
        }
        participant_id = asyncio.run(self.service.add_participant(data))
        row = get_participant_by_id(participant_id)
        self.assertIsNone(row['Department'])

    def test_candidate_department_cleared_on_update(self):
        start = {
            'FullNameRU': 'User B',
            'Gender': 'F',
            'Size': 'S',
            'Church': 'Test',
            'Role': 'TEAM',
            'Department': 'Media',
        }
        pid = asyncio.run(self.service.add_participant(start))
        update = {'Role': 'CANDIDATE', 'Department': 'Media', 'FullNameRU': 'User B', 'Gender': 'F', 'Size': 'S', 'Church': 'Test'}
        asyncio.run(self.service.update_participant(pid, update))
        row = get_participant_by_id(pid)
        self.assertEqual(row['Role'], 'CANDIDATE')
        self.assertIsNone(row['Department'])


if __name__ == '__main__':
    unittest.main()
