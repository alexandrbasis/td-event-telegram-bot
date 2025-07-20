import unittest
from main import parse_confirmation_template

class ConfirmationTemplateTestCase(unittest.TestCase):
    def test_basic_parse(self):
        text = "\n".join([
            "Имя (рус): Ирина Цой",
            "Пол: F",
            "Размер: M",
        ])
        data = parse_confirmation_template(text)
        self.assertEqual(data, {
            'FullNameRU': 'Ирина Цой',
            'Gender': 'F',
            'Size': 'M'
        })

    def test_ignore_service_values(self):
        text = "\n".join([
            "Имя (рус): Ирина Цой",
            "Пол: F",
            "Размер: ❌ Не указано",
            "Департамент: ➖ Не указано",
        ])
        data = parse_confirmation_template(text)
        self.assertEqual(data, {
            'FullNameRU': 'Ирина Цой',
            'Gender': 'F'
        })

    def test_church_parsing(self):
        text = "\n".join([
            "Имя (рус): Ирина Цой",
            "Церковь: церковь Грейс",
        ])
        data = parse_confirmation_template(text)
        self.assertEqual(data, {
            'FullNameRU': 'Ирина Цой',
            'Church': 'церковь Грейс'
        })

if __name__ == '__main__':
    unittest.main()
