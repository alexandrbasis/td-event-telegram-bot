import unittest
from parsers.participant_parser import normalize_field_value

# Нормализатор инициализируется автоматически, не нужно загружать кэш

class NormalizeFieldValueTestCase(unittest.TestCase):
    def test_unknown_department(self):
        self.assertEqual(normalize_field_value('Department', 'лалалал'), '')

    def test_unknown_gender(self):
        self.assertEqual(normalize_field_value('Gender', 'неизвестно'), '')

    def test_unknown_size(self):
        self.assertEqual(normalize_field_value('Size', 'большой'), '')

    def test_unknown_role(self):
        self.assertEqual(normalize_field_value('Role', 'работник'), 'CANDIDATE')

    def test_known_department_synonym(self):
        self.assertEqual(normalize_field_value('Department', 'админ'), 'Administration')

    def test_known_gender_synonym(self):
        self.assertEqual(normalize_field_value('Gender', 'муж'), 'M')

    def test_known_size_synonym(self):
        self.assertEqual(normalize_field_value('Size', 'medium'), 'M')

    def test_known_role_synonym(self):
        self.assertEqual(normalize_field_value('Role', 'тим'), 'TEAM')

if __name__ == '__main__':
    unittest.main()
