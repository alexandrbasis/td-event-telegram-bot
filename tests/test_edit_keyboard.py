import unittest
from services.participant_service import get_edit_keyboard


class EditKeyboardTestCase(unittest.TestCase):
    def test_candidate_hides_department(self):
        kb = get_edit_keyboard({"Role": "CANDIDATE"})
        rows = kb.inline_keyboard
        datas = [b.callback_data for row in rows for b in row]
        self.assertIn("edit_Role", datas)
        self.assertNotIn("edit_Department", datas)
        role_row = next(row for row in rows if any(b.callback_data == "edit_Role" for b in row))
        self.assertEqual(len(role_row), 1)

    def test_team_shows_department(self):
        kb = get_edit_keyboard({"Role": "TEAM"})
        rows = kb.inline_keyboard
        datas = [b.callback_data for row in rows for b in row]
        self.assertIn("edit_Department", datas)
        role_row = next(row for row in rows if any(b.callback_data == "edit_Role" for b in row))
        self.assertEqual(len(role_row), 2)


if __name__ == "__main__":
    unittest.main()
