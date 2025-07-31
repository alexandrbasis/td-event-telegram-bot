import unittest
from utils.field_normalizer import (
    field_normalizer,
    normalize_gender,
    normalize_role,
    normalize_size,
    normalize_department,
)


class FieldNormalizerTestCase(unittest.TestCase):
    def test_gender_normalization(self):
        """Тестирует нормализацию пола"""
        # Мужской пол
        self.assertEqual(normalize_gender('M'), 'M')
        self.assertEqual(normalize_gender('муж'), 'M')
        self.assertEqual(normalize_gender('мужской'), 'M')
        self.assertEqual(normalize_gender('male'), 'M')

        # Женский пол
        self.assertEqual(normalize_gender('F'), 'F')
        self.assertEqual(normalize_gender('жен'), 'F')
        self.assertEqual(normalize_gender('женский'), 'F')
        self.assertEqual(normalize_gender('female'), 'F')

        # Неизвестные значения
        self.assertIsNone(normalize_gender('неизвестно'))
        self.assertIsNone(normalize_gender(''))

    def test_role_normalization(self):
        """Тестирует нормализацию ролей"""
        # Team роли
        self.assertEqual(normalize_role('team'), 'TEAM')
        self.assertEqual(normalize_role('команда'), 'TEAM')
        self.assertEqual(normalize_role('тим'), 'TEAM')
        self.assertEqual(normalize_role('служитель'), 'TEAM')

        # Candidate роли
        self.assertEqual(normalize_role('candidate'), 'CANDIDATE')
        self.assertEqual(normalize_role('кандидат'), 'CANDIDATE')
        self.assertEqual(normalize_role('участник'), 'CANDIDATE')

        # Неизвестные значения
        self.assertIsNone(normalize_role('неизвестно'))

    def test_size_normalization(self):
        """Тестирует нормализацию размеров"""
        self.assertEqual(normalize_size('M'), 'M')
        self.assertEqual(normalize_size('medium'), 'M')
        self.assertEqual(normalize_size('медиум'), 'M')

        self.assertEqual(normalize_size('L'), 'L')
        self.assertEqual(normalize_size('large'), 'L')

        self.assertEqual(normalize_size('XL'), 'XL')
        self.assertEqual(normalize_size('extra large'), 'XL')

        # Неизвестные размеры
        self.assertIsNone(normalize_size('огромный'))

    def test_department_normalization(self):
        """Тестирует нормализацию департаментов"""
        self.assertEqual(normalize_department('админ'), 'Administration')
        self.assertEqual(normalize_department('admin'), 'Administration')
        self.assertEqual(normalize_department('администрация'), 'Administration')

        self.assertEqual(normalize_department('worship'), 'Worship')
        self.assertEqual(normalize_department('воршип'), 'Worship')
        self.assertEqual(normalize_department('прославление'), 'Worship')

        self.assertEqual(normalize_department('кухня'), 'Kitchen')
        self.assertEqual(normalize_department('kitchen'), 'Kitchen')

        # Неизвестные департаменты
        self.assertIsNone(normalize_department('неизвестный'))

    def test_confidence_scoring(self):
        """Тестирует scoring уверенности"""
        result = field_normalizer.normalize_gender('мужской')
        self.assertIsNotNone(result)
        self.assertEqual(result.normalized_value, 'M')
        self.assertEqual(result.confidence, 1.0)
        self.assertTrue(result.is_confident)

    def test_case_insensitive(self):
        """Тестирует нечувствительность к регистру"""
        self.assertEqual(normalize_gender('МУЖ'), 'M')
        self.assertEqual(normalize_gender('муж'), 'M')
        self.assertEqual(normalize_gender('Муж'), 'M')
        self.assertEqual(normalize_gender('МуЖ'), 'M')

    def test_whitespace_handling(self):
        """Тестирует обработку пробелов"""
        self.assertEqual(normalize_gender(' муж '), 'M')
        self.assertEqual(normalize_size(' medium '), 'M')
        self.assertEqual(normalize_role(' команда '), 'TEAM')


if __name__ == '__main__':
    unittest.main()
