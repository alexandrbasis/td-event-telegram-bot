import unittest
from services.participant_service import (
    get_edit_keyboard,
    get_gender_selection_keyboard_simple,
    get_role_selection_keyboard,
    get_size_selection_keyboard,
    get_department_selection_keyboard,
    get_gender_selection_keyboard_required,
    get_role_selection_keyboard_required,
    get_size_selection_keyboard_required,
    get_department_selection_keyboard_required,
)


class EditKeyboardTestCase(unittest.TestCase):
    def test_candidate_hides_department(self):
        kb = get_edit_keyboard({"Role": "CANDIDATE"})
        rows = kb.inline_keyboard
        datas = [b.callback_data for row in rows for b in row]
        self.assertIn("edit_Role", datas)
        self.assertNotIn("edit_Department", datas)
        role_row = next(
            row for row in rows if any(b.callback_data == "edit_Role" for b in row)
        )
        self.assertEqual(len(role_row), 1)

    def test_team_shows_department(self):
        kb = get_edit_keyboard({"Role": "TEAM"})
        rows = kb.inline_keyboard
        datas = [b.callback_data for row in rows for b in row]
        self.assertIn("edit_Department", datas)
        role_row = next(
            row for row in rows if any(b.callback_data == "edit_Role" for b in row)
        )
        self.assertEqual(len(role_row), 2)

    def test_gender_selection_keyboard(self):
        kb = get_gender_selection_keyboard_simple()
        datas = [b.callback_data for row in kb.inline_keyboard for b in row]
        self.assertIn("gender_M", datas)
        self.assertIn("gender_F", datas)
        self.assertIn("field_edit_cancel", datas)

    def test_role_selection_keyboard(self):
        kb = get_role_selection_keyboard()
        datas = [b.callback_data for row in kb.inline_keyboard for b in row]
        self.assertIn("role_CANDIDATE", datas)
        self.assertIn("role_TEAM", datas)
        self.assertIn("manual_input_Role", datas)
        self.assertIn("field_edit_cancel", datas)

    def test_size_selection_keyboard(self):
        kb = get_size_selection_keyboard()
        datas = [b.callback_data for row in kb.inline_keyboard for b in row]
        self.assertIn("size_XS", datas)
        self.assertIn("size_M", datas)
        self.assertIn("field_edit_cancel", datas)

    def test_department_selection_keyboard(self):
        kb = get_department_selection_keyboard()
        datas = [b.callback_data for row in kb.inline_keyboard for b in row]
        self.assertIn("dept_ROE", datas)
        self.assertIn("dept_Kitchen", datas)
        self.assertIn("manual_input_Department", datas)
        self.assertIn("field_edit_cancel", datas)

    def test_required_keyboards_no_manual_input(self):
        kb_role = get_role_selection_keyboard_required()
        datas_role = [b.callback_data for row in kb_role.inline_keyboard for b in row]
        self.assertNotIn("manual_input_Role", datas_role)

        kb_size = get_size_selection_keyboard_required()
        datas_size = [b.callback_data for row in kb_size.inline_keyboard for b in row]
        self.assertNotIn("manual_input_Size", datas_size)

        kb_dept = get_department_selection_keyboard_required()
        datas_dept = [b.callback_data for row in kb_dept.inline_keyboard for b in row]
        self.assertNotIn("manual_input_Department", datas_dept)

        kb_gender = get_gender_selection_keyboard_required()
        datas_gender = [b.callback_data for row in kb_gender.inline_keyboard for b in row]
        self.assertNotIn("manual_input_Gender", datas_gender)


if __name__ == "__main__":
    unittest.main()
