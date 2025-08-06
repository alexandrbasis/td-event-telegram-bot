import unittest
import sqlite3
from src.database import add_participant, get_participant_by_id, init_database

# Временно переопределяем путь к БД для тестов
import src.database as database

database.DB_PATH = ":memory:"

class DatabaseTestCase(unittest.TestCase):
    def setUp(self):
        """Создает чистую БД в памяти перед каждым тестом."""
        # Создаем одно соединение, которое будет использоваться во всех вызовах
        self.conn = sqlite3.connect(database.DB_PATH)
        self.conn.row_factory = sqlite3.Row
        # Патчим DatabaseConnection, чтобы возвращать уже созданное соединение
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
        self.participant_data = {
            'FullNameRU': 'Тестовый Участник',
            'Gender': 'M',
            'Size': 'L',
            'Church': 'Тестовая Церковь',
            'Role': 'CANDIDATE',
        }

    def tearDown(self):
        # Возвращаем исходные методы и закрываем соединение
        database.DatabaseConnection.__enter__ = self._original_enter
        database.DatabaseConnection.__exit__ = self._original_exit
        self.conn.close()

    def test_add_and_get_participant(self):
        """Тест: можно ли добавить участника и затем получить его по ID."""
        participant_id = add_participant(self.participant_data)
        self.assertIsNotNone(participant_id)

        retrieved_participant = get_participant_by_id(participant_id)
        self.assertIsNotNone(retrieved_participant)

        self.assertEqual(retrieved_participant['FullNameRU'], 'Тестовый Участник')
        self.assertEqual(retrieved_participant['Role'], 'CANDIDATE')


if __name__ == '__main__':
    unittest.main()
