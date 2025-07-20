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

if __name__ == '__main__':
    unittest.main()
