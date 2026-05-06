"""
Tests for URL configuration and endpoints in task_manager/urls.py

These tests use mocking to avoid touching the real filesystem.
"""
from unittest.mock import patch, mock_open
from django.test import TestCase, Client
from django.urls import reverse


class HealthCheckViewTestCase(TestCase):
    """Tests for health_check endpoint."""

    def setUp(self):
        self.client = Client()

    def test_health_check_returns_200(self):
        """Test health check endpoint returns 200 OK."""
        response = self.client.get(reverse('health'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode('utf-8'), 'ok')

    def test_health_check_uses_require_get_decorator(self):
        """Test that health_check only accepts GET requests."""
        # POST request should return 405 Method Not Allowed
        response = self.client.post(reverse('health'))

        self.assertEqual(response.status_code, 405)


class AssetLinksViewTestCase(TestCase):
    """
    Tests for AssetLinksView endpoint.

    Uses mocking to test both success and failure cases without
    modifying the real filesystem.
    """

    def setUp(self):
        self.client = Client()

    @patch(
        'task_manager.urls.os.path.exists',
        return_value=True
    )
    @patch(
        'task_manager.urls.open',
        new_callable=mock_open,
        read_data=b'{"android": []}'
    )
    def test_assetlinks_view_returns_file_when_exists(
        self, mock_file, mock_exists
    ):
        """
        Test assetlinks endpoint returns file content when file exists.

        Uses mocks to simulate file existence without touching real filesystem.
        """
        response = self.client.get('/.well-known/assetlinks.json')

        self.assertEqual(response.status_code, 200)
        # FileResponse uses streaming_content
        response_content = b''.join(response.streaming_content)
        self.assertEqual(response_content, b'{"android": []}')
        self.assertEqual(response['Content-Type'], 'application/json')

    @patch('task_manager.urls.os.path.exists', return_value=False)
    def test_assetlinks_view_returns_404_when_file_missing(self, mock_exists):
        """
        Test assetlinks endpoint returns 404 when file is missing.

        Uses mock to simulate missing file without touching real filesystem.
        """
        response = self.client.get('/.well-known/assetlinks.json')

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {'error': 'Not found'})
