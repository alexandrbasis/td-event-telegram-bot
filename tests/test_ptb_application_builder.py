import unittest


class PTBApplicationBuilderStabilityTest(unittest.TestCase):
    def test_application_builder_build_does_not_raise(self):
        # Arrange: use dummy token to avoid any network operations
        from telegram.ext import Application

        # Act & Assert: build should not raise due to Updater slots or similar issues
        try:
            app = Application.builder().token("DUMMY").build()
            self.assertIsNotNone(app)
            # Ensure we are not running, and we don't start polling in this test
            self.assertFalse(app.running)
        except Exception as exc:
            self.fail(f"Application.builder().build() raised unexpectedly: {exc}")


if __name__ == "__main__":
    unittest.main()


