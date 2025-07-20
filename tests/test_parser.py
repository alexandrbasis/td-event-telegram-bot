import unittest
from parsers.participant_parser import parse_participant_data

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

if __name__ == '__main__':
    unittest.main()
