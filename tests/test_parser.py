import unittest
from parsers.participant_parser import (
    parse_participant_data,
    is_template_format,
    parse_template_format,
    parse_unstructured_text,
)
from utils.cache import load_reference_data, cache

load_reference_data()

class ParserTestCase(unittest.TestCase):
    def test_parse_candidate(self):
        text = "Иван Петров M L церковь Новая Жизнь кандидат"
        data = parse_participant_data(text)
        self.assertEqual(data['FullNameRU'], 'Иван Петров')
        self.assertEqual(data['Gender'], 'M')
        self.assertEqual(data['Size'], 'L')
        self.assertEqual(data['Role'], 'CANDIDATE')

    def test_parse_team_with_department(self):
        text = "Анна Иванова F S церковь Благодать команда worship"
        data = parse_participant_data(text)
        self.assertEqual(data['Role'], 'TEAM')
        self.assertEqual(data['Department'], 'Worship')

    def test_parse_department_with_quotes(self):
        text = "Иван Петров M команда 'worship'"
        data = parse_participant_data(text)
        self.assertEqual(data['Department'], 'Worship')

    def test_russian_size_and_gender_priority(self):
        text = "Ольга Сергеевна жен М Афула церковь Благодать"
        data = parse_participant_data(text)
        self.assertEqual(data['Gender'], 'F')
        self.assertEqual(data['Size'], '')
        self.assertEqual(data['CountryAndCity'], 'Афула')
        self.assertEqual(data['Church'], 'церковь Благодать')

    def test_update_gender_only(self):
        text = "Пол женский"
        data = parse_participant_data(text, is_update=True)
        self.assertEqual(data, {'Gender': 'F'})

    def test_size_medium_synonym(self):
        text = "размер medium"
        data = parse_participant_data(text, is_update=True)
        self.assertEqual(data, {'Size': 'M'})

    def test_template_parsing(self):
        text = "Имя (рус): Иван Петров, Пол: M, Размер: L, Церковь: Благодать"
        self.assertTrue(is_template_format(text))
        data = parse_participant_data(text)
        self.assertEqual(data['FullNameRU'], 'Иван Петров')
        self.assertEqual(data['Gender'], 'M')
        self.assertEqual(data['Size'], 'L')
        self.assertEqual(data['Church'], 'Благодать')

    def test_medium_size_not_in_submitted_by(self):
        """Тест проверяет, что 'medium' распознается как размер, а не как часть имени подавшего"""
        text = "Тест Басис тим админ община грейс муж Хайфа от Ирина Цой medium"
        data = parse_participant_data(text)
        
        self.assertEqual(data['FullNameRU'], 'Тест Басис')
        self.assertEqual(data['Gender'], 'M')
        self.assertEqual(data['Size'], 'M')  # medium должен стать M
        self.assertEqual(data['Role'], 'TEAM')
        self.assertEqual(data['Department'], 'Administration')
        self.assertEqual(data['Church'], 'община грейс')
        self.assertEqual(data['CountryAndCity'], 'Хайфа')
        self.assertEqual(data['SubmittedBy'], 'Ирина Цой')  # без 'medium'

    def test_contact_validation(self):
        """Тест проверяет валидацию контактной информации"""
        # Некорректные контакты не должны распознаваться
        text1 = "Иван Петров муж L церковь Грейс кандидат Н"
        data1 = parse_participant_data(text1)
        self.assertEqual(data1['ContactInformation'], '')  # Н не должно быть контактом

        # Корректные телефоны должны распознаваться
        text2 = "Иван Петров муж L церковь Грейс кандидат +972501234567"
        data2 = parse_participant_data(text2)
        self.assertEqual(data2['ContactInformation'], '+972501234567')

        # Корректные email должны распознаваться
        text3 = "Иван Петров муж L церковь Грейс кандидат ivan@mail.ru"
        data3 = parse_participant_data(text3)
        self.assertEqual(data3['ContactInformation'], 'ivan@mail.ru')

        # Некорректные 'телефоны' не должны распознаваться
        text4 = "Иван Петров муж L церковь Грейс кандидат 123"
        data4 = parse_participant_data(text4)
        self.assertEqual(data4['ContactInformation'], '')  # 123 слишком короткий

    def test_is_template_format_variants(self):
        self.assertTrue(is_template_format("Имя (рус): Иван\nПол: M\nЦерковь: XYZ"))
        self.assertFalse(is_template_format("Просто текст без шаблона"))

    def test_parse_template_partial(self):
        text = "Имя (рус): Иван Петров\nПол: M\nРазмер:\nЦерковь: Благодать"
        data = parse_template_format(text)
        self.assertEqual(data['FullNameRU'], 'Иван Петров')
        self.assertEqual(data['Gender'], 'M')
        self.assertEqual(data['Size'], '')
        self.assertEqual(data['Church'], 'Благодать')

    def test_parse_template_single_line_commas(self):
        text = "Имя (рус): Иван, Пол: M, Размер: L, Церковь: Благодать"
        data = parse_template_format(text)
        self.assertEqual(data['FullNameRU'], 'Иван')
        self.assertEqual(data['Gender'], 'M')
        self.assertEqual(data['Size'], 'L')
        self.assertEqual(data['Church'], 'Благодать')

    def test_template_normalization(self):
        text = "\n".join([
            "Имя (рус): Иван Петров",
            "Пол: муж",
            "Размер: extra large",
            "Роль: тим",
            "Департамент: админ",
        ])
        data = parse_participant_data(text)
        self.assertEqual(data['Gender'], 'M')
        self.assertEqual(data['Size'], 'XL')
        self.assertEqual(data['Role'], 'TEAM')
        self.assertEqual(data['Department'], 'Administration')

    def test_template_unknown_department(self):
        text = "\n".join([
            "Имя (рус): Иван",
            "Пол: M",
            "Департамент: Support",
        ])
        data = parse_participant_data(text)
        self.assertEqual(data['Department'], '')

    def test_unstructured_multi_field(self):
        cache.set('churches', ['Грейс'])
        text = "Саша Б тим админ Грейс Хайфа"
        data = parse_unstructured_text(text)
        self.assertEqual(data['FullNameRU'], 'Саша Б')
        self.assertEqual(data['Role'], 'TEAM')
        self.assertEqual(data['Department'], 'Administration')
        self.assertEqual(data['Church'], 'Грейс')
        self.assertEqual(data['CountryAndCity'], 'ХАЙФА')

if __name__ == '__main__':
    unittest.main()
