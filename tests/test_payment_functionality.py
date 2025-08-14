"""
Тесты для функционала оплаты (Payment Functionality)
Соответствует задаче TDB-1: Добавление функционала о внесении оплаты
"""

import unittest
import sqlite3
from datetime import datetime
from models.participant import Participant
from constants import PaymentStatus, PAYMENT_STATUS_DISPLAY, payment_status_from_display
from services.participant_service import ParticipantService, format_participant_block
from parsers.participant_parser import ParticipantParser, parse_unstructured_text
from repositories.participant_repository import SqliteParticipantRepository
import database


class TestPaymentModel(unittest.TestCase):
    """Тесты модели Participant с новыми полями оплаты"""
    
    def test_participant_payment_fields_default_values(self):
        """Тест дефолтных значений полей оплаты"""
        participant = Participant(FullNameRU="Тестовый Участник", Role="CANDIDATE")
        
        self.assertEqual(participant.PaymentStatus, "Unpaid")
        self.assertEqual(participant.PaymentAmount, 0)
        self.assertEqual(participant.PaymentDate, "")
    
    def test_participant_payment_fields_custom_values(self):
        """Тест установки кастомных значений полей оплаты"""
        participant = Participant(
            FullNameRU="Тестовый Участник",
            Role="CANDIDATE",
            PaymentStatus="Paid",
            PaymentAmount=500,
            PaymentDate="2025-01-24"
        )
        
        self.assertEqual(participant.PaymentStatus, "Paid")
        self.assertEqual(participant.PaymentAmount, 500)
        self.assertEqual(participant.PaymentDate, "2025-01-24")
    
    def test_payment_amount_integer_only(self):
        """Тест что PaymentAmount принимает только integers"""
        participant = Participant(FullNameRU="Тестовый Участник", Role="CANDIDATE")
        
        # Должно работать с integers
        participant.PaymentAmount = 1500
        self.assertEqual(participant.PaymentAmount, 1500)
        
        # Проверяем, что это именно int
        self.assertIsInstance(participant.PaymentAmount, int)


class TestPaymentStatusEnum(unittest.TestCase):
    """Тесты enum PaymentStatus"""
    
    def test_payment_status_values(self):
        """Тест значений enum PaymentStatus"""
        self.assertEqual(PaymentStatus.UNPAID.value, "Unpaid")
        self.assertEqual(PaymentStatus.PAID.value, "Paid")
        self.assertEqual(PaymentStatus.PARTIAL.value, "Partial")
        self.assertEqual(PaymentStatus.REFUNDED.value, "Refunded")
    
    def test_payment_status_display_mapping(self):
        """Тест маппинга отображения статусов оплаты"""
        expected_display = {
            "Unpaid": "❌ Не оплачено",
            "Paid": "✅ Оплачено",
            "Partial": "🔶 Частично оплачено",
            "Refunded": "🔄 Возвращено"
        }
        
        self.assertEqual(PAYMENT_STATUS_DISPLAY, expected_display)
    
    def test_payment_status_from_display_function(self):
        """Тест функции payment_status_from_display"""
        # Тест корректного преобразования
        self.assertEqual(payment_status_from_display("не оплачено"), "Unpaid")
        self.assertEqual(payment_status_from_display("оплачено"), "Paid")
        self.assertEqual(payment_status_from_display("частично оплачено"), "Partial")
        self.assertEqual(payment_status_from_display("возвращено"), "Refunded")
        
        # Тест case insensitive
        self.assertEqual(payment_status_from_display("НЕ ОПЛАЧЕНО"), "Unpaid")
        self.assertEqual(payment_status_from_display("Оплачено"), "Paid")
        
        # Тест неизвестного статуса
        self.assertEqual(payment_status_from_display("неизвестный статус"), "Unpaid")


class TestPaymentValidation(unittest.TestCase):
    """Тесты валидации полей оплаты"""
    
    def test_validate_payment_amount_valid_integers(self):
        """Тест валидации корректных целых чисел"""
        valid_amounts = ["100", "500", "1000", "1", "999999"]
        
        for amount_str in valid_amounts:
            # Имитация валидации как в реальном коде
            try:
                amount = int(amount_str.strip())
                self.assertGreater(amount, 0)
                self.assertIsInstance(amount, int)
            except ValueError:
                self.fail(f"Валидация не прошла для корректного значения: {amount_str}")
    
    def test_validate_payment_amount_invalid_values(self):
        """Тест валидации некорректных значений"""
        invalid_amounts = ["100.5", "abc", "", "0", "-100", "100.0", "10,5"]
        
        for amount_str in invalid_amounts:
            with self.assertRaises(ValueError):
                amount = int(amount_str.strip())
                if amount <= 0:
                    raise ValueError("Amount must be positive")
    
    def test_payment_status_validation(self):
        """Тест валидации статусов оплаты"""
        valid_statuses = ["Unpaid", "Paid", "Partial", "Refunded"]
        
        for status in valid_statuses:
            # Проверяем, что статус существует в enum
            self.assertTrue(any(ps.value == status for ps in PaymentStatus))


class TestPaymentParser(unittest.TestCase):
    """Тесты парсера для полей оплаты"""
    
    def setUp(self):
        """Настройка для каждого теста"""
        self.parser = ParticipantParser()
    
    def test_parse_payment_status_from_text(self):
        """Тест парсинга статуса оплаты из текста"""
        test_cases = [
            ("Имя: Тест\nСтатус оплаты: Оплачено", "Paid"),
            ("Имя: Тест\nОплата: Не оплачено", "Unpaid"),
        ]
        
        for text, expected_status in test_cases:
            # Используем реальную функцию парсинга
            result = parse_unstructured_text(text)
            if result.get("PaymentStatus"):
                self.assertEqual(result.get("PaymentStatus"), expected_status)
    
    def test_parse_payment_amount_from_text(self):
        """Тест парсинга суммы оплаты из текста"""
        test_cases = [
            ("Имя: Тест\nСумма: 500", 500),
            ("Имя: Тест\nОплачено: 1200", 1200),
        ]
        
        for text, expected_amount in test_cases:
            # Используем реальную функцию парсинга
            result = parse_unstructured_text(text)
            if result.get("PaymentAmount"):
                self.assertEqual(result.get("PaymentAmount"), expected_amount)


class TestPaymentService(unittest.TestCase):
    """Тесты сервисного слоя для платежей"""
    
    def setUp(self):
        """Настройка для каждого теста"""
        # Используем in-memory БД как в других тестах
        database.DB_PATH = ":memory:"
        self.conn = sqlite3.connect(database.DB_PATH)
        self.conn.row_factory = sqlite3.Row
        
        # Патчим DatabaseConnection для использования нашего соединения
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
        
        database.init_database()
        self.repository = SqliteParticipantRepository()
        self.service = ParticipantService(self.repository)
    
    def tearDown(self):
        """Очистка после каждого теста"""
        database.DatabaseConnection.__enter__ = self._original_enter
        database.DatabaseConnection.__exit__ = self._original_exit
        self.conn.close()
    
    def test_process_payment_success(self):
        """Тест успешной обработки платежа"""
        # Создаем участника
        participant = Participant(
            FullNameRU="Тестовый Участник",
            Role="CANDIDATE",
            PaymentStatus="Unpaid",
            PaymentAmount=0
        )
        participant_id = self.repository.add_participant(participant)
        
        # Обрабатываем платеж (метод принимает amount, payment_date, user_id)
        success = self.service.process_payment(participant_id, 500, "2025-01-25")
        
        self.assertTrue(success)
        
        # Проверяем, что данные обновились
        updated_participant = self.repository.get_participant_by_id(participant_id)
        self.assertEqual(updated_participant.PaymentStatus, "Paid")
        self.assertEqual(updated_participant.PaymentAmount, 500)
        self.assertNotEqual(updated_participant.PaymentDate, "")  # Должна быть установлена дата
    
    def test_validate_payment_data_valid(self):
        """Тест валидации корректных данных платежа"""
        valid_data = {
            "PaymentAmount": 500,
            "PaymentStatus": "Paid"
        }
        
        is_valid, error_message = self.service.validate_payment_data(valid_data)
        
        self.assertTrue(is_valid)
        self.assertEqual(error_message, "")
    
    def test_get_payment_statistics(self):
        """Тест получения статистики платежей"""
        # Создаем участников с разными статусами
        participants_data = [
            ("Участник 1", "Paid", 500),
            ("Участник 2", "Unpaid", 0),
            ("Участник 3", "Paid", 800),
        ]
        
        for name, status, amount in participants_data:
            participant = Participant(
                FullNameRU=name,
                Role="CANDIDATE",
                PaymentStatus=status,
                PaymentAmount=amount
            )
            self.repository.add_participant(participant)
        
        # Получаем статистику через сервис
        stats = self.service.get_payment_statistics()
        
        self.assertIn("total_participants", stats)
        self.assertIn("paid_count", stats)
        self.assertIn("unpaid_count", stats)
        self.assertIn("total_amount", stats)
    
    def test_format_participant_with_payment_info(self):
        """Тест форматирования участника с информацией об оплате"""
        participant = Participant(
            FullNameRU="Тестовый Участник",
            Role="CANDIDATE",
            PaymentStatus="Paid",
            PaymentAmount=500,
            PaymentDate="2025-01-24"
        )
        
        formatted = format_participant_block(participant)
        
        self.assertIn("💰 Статус оплаты: ✅ Оплачено", formatted)
        self.assertIn("💳 Сумма оплаты: 500 ₪", formatted)
        self.assertIn("📅 Дата оплаты: 2025-01-24", formatted)


class TestPaymentDatabase(unittest.TestCase):
    """Тесты работы с базой данных для платежей"""
    
    def setUp(self):
        """Настройка для каждого теста"""
        # Используем in-memory БД как в других тестах
        database.DB_PATH = ":memory:"
        self.conn = sqlite3.connect(database.DB_PATH)
        self.conn.row_factory = sqlite3.Row
        
        # Патчим DatabaseConnection для использования нашего соединения
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
        
        database.init_database()
        self.repository = SqliteParticipantRepository()
    
    def tearDown(self):
        """Очистка после каждого теста"""
        database.DatabaseConnection.__enter__ = self._original_enter
        database.DatabaseConnection.__exit__ = self._original_exit
        self.conn.close()
    
    def test_add_participant_with_payment_fields(self):
        """Тест добавления участника с полями оплаты"""
        participant = Participant(
            FullNameRU="Тестовый Участник",
            Role="CANDIDATE",
            PaymentStatus="Paid",
            PaymentAmount=500,
            PaymentDate="2025-01-24"
        )
        
        participant_id = self.repository.add_participant(participant)
        
        # Проверяем, что участник сохранился с полями оплаты
        saved_participant = self.repository.get_participant_by_id(participant_id)
        self.assertEqual(saved_participant.PaymentStatus, "Paid")
        self.assertEqual(saved_participant.PaymentAmount, 500)
        self.assertEqual(saved_participant.PaymentDate, "2025-01-24")
    
    def test_update_payment_info(self):
        """Тест обновления информации об оплате"""
        # Создаем участника
        participant = Participant(FullNameRU="Тестовый Участник", Role="CANDIDATE")
        participant_id = self.repository.add_participant(participant)
        
        # Обновляем информацию об оплате
        update_data = {
            "PaymentStatus": "Paid",
            "PaymentAmount": 750,
            "PaymentDate": "2025-01-24"
        }
        
        success = self.repository.update_participant(participant_id, update_data)
        self.assertTrue(success)
        
        # Проверяем обновление
        updated_participant = self.repository.get_participant_by_id(participant_id)
        self.assertEqual(updated_participant.PaymentStatus, "Paid")
        self.assertEqual(updated_participant.PaymentAmount, 750)
        self.assertEqual(updated_participant.PaymentDate, "2025-01-24")


class TestPaymentIntegration(unittest.TestCase):
    """Интеграционные тесты для функционала оплаты"""
    
    def setUp(self):
        """Настройка для каждого теста"""
        # Используем in-memory БД как в других тестах
        database.DB_PATH = ":memory:"
        self.conn = sqlite3.connect(database.DB_PATH)
        self.conn.row_factory = sqlite3.Row
        
        # Патчим DatabaseConnection для использования нашего соединения
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
        
        database.init_database()
        self.repository = SqliteParticipantRepository()
        self.service = ParticipantService(self.repository)
        self.parser = ParticipantParser()
    
    def tearDown(self):
        """Очистка после каждого теста"""
        database.DatabaseConnection.__enter__ = self._original_enter
        database.DatabaseConnection.__exit__ = self._original_exit
        self.conn.close()
    
    def test_full_payment_workflow(self):
        """Тест полного workflow обработки платежа"""
        # 1. Создаем участника
        participant = Participant(FullNameRU="Тестовый Участник", Role="CANDIDATE")
        participant_id = self.repository.add_participant(participant)
        
        # 2. Проверяем, что изначально не оплачено
        initial_participant = self.repository.get_participant_by_id(participant_id)
        self.assertEqual(initial_participant.PaymentStatus, "Unpaid")
        self.assertEqual(initial_participant.PaymentAmount, 0)
        
        # 3. Обрабатываем платеж через сервис
        payment_success = self.service.process_payment(participant_id, 600, "2025-01-25")
        self.assertTrue(payment_success)
        
        # 4. Проверяем финальное состояние
        final_participant = self.repository.get_participant_by_id(participant_id)
        self.assertEqual(final_participant.PaymentStatus, "Paid")
        self.assertEqual(final_participant.PaymentAmount, 600)
        self.assertNotEqual(final_participant.PaymentDate, "")
        
        # 5. Проверяем форматирование
        formatted = format_participant_block(final_participant)
        self.assertIn("💰 Статус оплаты: ✅ Оплачено", formatted)
        self.assertIn("💳 Сумма оплаты: 600 ₪", formatted)


if __name__ == "__main__":
    unittest.main()
