import unittest

from main import get_missing_fields, get_missing_field_keys
from src.services.participant_service import FIELD_LABELS

class MissingFieldsTestCase(unittest.TestCase):
    def test_department_required_for_team(self):
        data = {
            "FullNameRU": "Иван Петров",
            "Gender": "M",
            "Size": "L",
            "Church": "Благодать",
            "Role": "TEAM",
            "Department": "",
        }
        fields = get_missing_field_keys(data)
        self.assertIn("Department", fields)
        labels = get_missing_fields(data)
        self.assertIn(FIELD_LABELS["Department"], labels)

if __name__ == "__main__":
    unittest.main()
