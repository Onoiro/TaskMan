from django.test import TestCase, Client
from unittest.mock import patch


class RollbarTriggerErrorTests(TestCase):
    def setUp(self):
        self.client = Client()

    @patch('rollbar.report_exc_info')  # замена Rollbar на mock-объект
    def test_trigger_error(self, mock_rollbar):
        """
        Test that a division by zero error occurs and Rollbar is called.
        """
        response = None
        try:
            response = self.client.get('/trigger-error/')
        except ZeroDivisionError:
            pass
        self.assertIsNone(response)
        self.assertTrue(mock_rollbar.called)
