import unittest

from src.utils.validators import validate_participant_data


class ValidateParticipantDataTestCase(unittest.TestCase):
    def test_valid_candidate(self):
        data = {
            "FullNameRU": "Иван Петров",
            "Gender": "M",
            "Size": "L",
            "Church": "Благодать",
            "Role": "CANDIDATE",
        }
        valid, error = validate_participant_data(data)
        self.assertTrue(valid)
        self.assertEqual(error, "")

    def test_missing_role_fails(self):
        data = {
            "FullNameRU": "Иван Петров",
            "Gender": "M",
            "Size": "L",
            "Church": "Благодать",
            "Role": "",
        }
        valid, error = validate_participant_data(data)
        self.assertFalse(valid)
        self.assertEqual(error, "Не указана роль")

    def test_invalid_role_fails(self):
        data = {
            "FullNameRU": "Иван Петров",
            "Gender": "M",
            "Size": "L",
            "Church": "Благодать",
            "Role": "UNKNOWN",
        }
        valid, error = validate_participant_data(data)
        self.assertFalse(valid)
        self.assertEqual(error, "Не указана роль")

    def test_missing_gender_fails(self):
        data = {
            "FullNameRU": "Иван Петров",
            "Gender": "",
            "Size": "L",
            "Church": "Благодать",
            "Role": "CANDIDATE",
        }
        valid, error = validate_participant_data(data)
        self.assertFalse(valid)
        self.assertEqual(error, "Пол должен быть M или F")

    def test_team_requires_department(self):
        data = {
            "FullNameRU": "Иван Петров",
            "Gender": "M",
            "Size": "L",
            "Church": "Благодать",
            "Role": "TEAM",
            "Department": "",
        }
        valid, error = validate_participant_data(data)
        self.assertFalse(valid)
        self.assertEqual(error, "Для роли TEAM необходимо указать департамент")

    def test_missing_size_fails(self):
        data = {
            "FullNameRU": "Иван Петров",
            "Gender": "M",
            "Size": "",
            "Church": "Благодать",
            "Role": "CANDIDATE",
        }
        valid, error = validate_participant_data(data)
        self.assertFalse(valid)
        self.assertEqual(error, "Недопустимый размер одежды")


if __name__ == "__main__":
    unittest.main()
