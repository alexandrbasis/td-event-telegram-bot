import unittest
from parsers.participant_parser import parse_template_format


class ConfirmationTemplateTestCase(unittest.TestCase):
    def test_basic_parse(self):
        text = "\n".join(
            [
                "Имя (рус): Ирина Цой",
                "Пол: F",
                "Размер: M",
            ]
        )
        data = parse_template_format(text)
        self.assertEqual(data, {"FullNameRU": "Ирина Цой", "Gender": "F", "Size": "M"})

    def test_ignore_service_values(self):
        text = "\n".join(
            [
                "Имя (рус): Ирина Цой",
                "Пол: F",
                "Размер: ❌ Не указано",
                "Департамент: ➖ Не указано",
            ]
        )
        data = parse_template_format(text)
        self.assertEqual(
            data,
            {"FullNameRU": "Ирина Цой", "Gender": "F", "Size": "", "Department": ""},
        )

    def test_church_parsing(self):
        text = "\n".join(
            [
                "Имя (рус): Ирина Цой",
                "Церковь: церковь Грейс",
            ]
        )
        data = parse_template_format(text)
        self.assertEqual(data, {"FullNameRU": "Ирина Цой", "Church": "церковь Грейс"})

    def test_parse_display_values(self):
        text = "\n".join(
            [
                "Имя (рус): Тест Тестов",
                "Пол: Мужской",
                "Роль: Команда",
                "Департамент: Кухня",
                "Размер: XL",
            ]
        )
        data = parse_template_format(text)
        self.assertEqual(
            data,
            {
                "FullNameRU": "Тест Тестов",
                "Gender": "M",
                "Role": "TEAM",
                "Department": "Kitchen",
                "Size": "XL",
            },
        )


if __name__ == "__main__":
    unittest.main()
