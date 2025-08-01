import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock
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


class SafeTimeoutJobTestCase(unittest.TestCase):
    def test_safe_job_creation_no_queue(self):
        from main import safe_create_timeout_job

        context = SimpleNamespace(user_data={}, job_queue=None)
        job = safe_create_timeout_job(context, lambda x: x, 5, user_id=1)
        self.assertIsNone(job)
        self.assertIn("edit_timeout", context.user_data)

    def test_safe_job_creation_with_queue(self):
        from main import safe_create_timeout_job

        mock_job = object()
        job_queue = MagicMock()
        job_queue.run_once.return_value = mock_job
        context = SimpleNamespace(user_data={}, job_queue=job_queue)

        job = safe_create_timeout_job(context, lambda x: x, 5, user_id=2)
        job_queue.run_once.assert_called_once()
        self.assertIs(job, mock_job)


if __name__ == "__main__":
    unittest.main()
