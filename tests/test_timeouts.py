import unittest
from types import SimpleNamespace
from utils.timeouts import set_edit_timeout, is_edit_expired, clear_expired_edit
import time


class TimeoutsTestCase(unittest.TestCase):
    def setUp(self):
        self.context = SimpleNamespace(user_data={})

    def test_set_and_expire(self):
        set_edit_timeout(self.context, user_id=1, timeout_seconds=0.1)
        self.assertFalse(is_edit_expired(self.context))
        time.sleep(0.2)
        self.assertTrue(is_edit_expired(self.context))
        cleared = clear_expired_edit(self.context)
        self.assertTrue(cleared)
        self.assertNotIn("field_to_edit", self.context.user_data)


if __name__ == "__main__":
    unittest.main()
