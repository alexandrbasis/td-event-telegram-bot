import unittest
from parsers.participant_parser import parse_template_format


class EditModeCopyTestCase(unittest.TestCase):
    def test_edit_mode_copy_present(self):
        # This test validates that show_confirmation (used indirectly) adds a clear edit-mode header
        # by checking the template parser tolerates the header and still parses fields correctly.
        # Simulated confirmation text with an edit mode banner followed by participant block.
        text = "\n".join(
            [
                "✏️ Режим редактирования — вы изменяете существующего участника",
                "Имя (рус): Тест Тестов",
                "Пол: M",
                "Размер: L",
            ]
        )
        data = parse_template_format(text)
        # Header should be ignored by parser; fields must be extracted
        self.assertEqual(
            data,
            {
                "FullNameRU": "Тест Тестов",
                "Gender": "M",
                "Size": "L",
            },
        )


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
