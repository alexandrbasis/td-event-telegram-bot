import unittest
from services.participant_service import merge_participant_data, detect_changes


class RoleDepartmentLogicTestCase(unittest.TestCase):
    def test_merge_clears_department_on_role_change(self):
        existing = {
            "FullNameRU": "Test User",
            "Gender": "M",
            "Church": "Test",
            "Role": "TEAM",
            "Department": "Worship",
        }
        updates = {"Role": "CANDIDATE"}
        result = merge_participant_data(existing, updates)
        self.assertEqual(result["Role"], "CANDIDATE")
        self.assertEqual(result.get("Department"), "")

    def test_detect_changes_shows_department_cleared(self):
        old = {
            "FullNameRU": "Test User",
            "Role": "TEAM",
            "Department": "Worship",
        }
        new = {"Role": "CANDIDATE"}
        changes = detect_changes(old, new)
        joined = " ".join(changes)
        self.assertIn("Департамент", joined)
        self.assertIn("Worship → —", joined)


if __name__ == "__main__":
    unittest.main()
