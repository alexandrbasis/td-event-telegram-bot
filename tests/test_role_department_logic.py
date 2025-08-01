import unittest
from services.participant_service import (
    merge_participant_data,
    detect_changes,
    update_single_field,
)


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

    def test_merge_clears_department_when_role_set_to_team(self):
        existing = {
            "FullNameRU": "Test User",
            "Gender": "M",
            "Church": "Test",
            "Role": "",
            "Department": "Worship",
        }
        updates = {"Role": "TEAM"}
        result = merge_participant_data(existing, updates)
        self.assertEqual(result["Role"], "TEAM")
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

    def test_update_single_field_resets_department_on_role_change(self):
        data = {"Role": "TEAM", "Department": "Worship"}
        updated, _ = update_single_field(data, "Role", "CANDIDATE")
        self.assertEqual(updated["Role"], "CANDIDATE")
        self.assertEqual(updated.get("Department"), "")


if __name__ == "__main__":
    unittest.main()
