import unittest
from parsers.participant_parser import (
    parse_participant_data,
    is_template_format,
)

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

if __name__ == '__main__':
    unittest.main()
