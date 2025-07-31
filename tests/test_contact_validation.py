import unittest

from parsers.participant_parser import is_valid_phone
from parsers.participant_parser import parse_participant_data


class IsraeliPhoneValidationTestCase(unittest.TestCase):
    def test_valid_israeli_phones(self):
        """Тест корректных израильских номеров"""
        valid_phones = [
            # Мобильные местные
            "050-123-4567",
            "052-123-4567",
            "053-123-4567",
            "054-123-4567",
            "055-123-4567",
            "058-123-4567",
            "0501234567",
            # Международные
            "+972-50-123-4567",
            "+972-52-123-4567",
            "+972501234567",
            "+972521234567",
            # Стационарные
            "02-123-4567",
            "03-123-4567",
            "04-123-4567",
            "08-123-4567",
            "09-123-4567",
            "+972-2-123-4567",
            # С различным форматированием
            "050 123 4567",
            "050.123.4567",
            "(050) 123-4567",
        ]

        for phone in valid_phones:
            with self.subTest(phone=phone):
                self.assertTrue(
                    is_valid_phone(phone), f"Should be valid Israeli phone: {phone}"
                )

    def test_invalid_israeli_phones(self):
        """Тест некорректных номеров"""
        invalid_phones = [
            "051-123-4567",
            "056-123-4567",
            "057-123-4567",
            "059-123-4567",
            "050-12-345",
            "050-123-45678",
            "01-123-4567",
            "05-123-4567",
            "07-123-4567",
            "+972-51-123-4567",
            "+972-1-123-4567",
            "12345",
            "050123456789012345",
            "0000000000",
            "1111111111",
        ]

        for phone in invalid_phones:
            with self.subTest(phone=phone):
                self.assertFalse(is_valid_phone(phone), f"Should be invalid: {phone}")

    def test_israeli_parser_integration(self):
        """Тест интеграции с парсером для израильских номеров"""
        result = parse_participant_data("Моше Коэн муж L церковь Грейс 050-123-4567")
        self.assertEqual(result["ContactInformation"], "050-123-4567")

        result = parse_participant_data(
            "Сара Леви жен M церковь Шалом +972-52-123-4567"
        )
        self.assertEqual(result["ContactInformation"], "+972-52-123-4567")

        result = parse_participant_data(
            "Авраам Иванов муж XL церковь Благодать 02-123-4567"
        )
        self.assertEqual(result["ContactInformation"], "02-123-4567")

        result = parse_participant_data("Ицхак Петров муж L церковь Грейс 051-123-4567")
        self.assertEqual(result["ContactInformation"], "")


if __name__ == "__main__":
    unittest.main()
