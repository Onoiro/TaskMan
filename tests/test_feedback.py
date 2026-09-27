import os
import urllib.error
from unittest.mock import MagicMock, patch

from django.test import TestCase, Client
from django.urls import reverse
from task_manager.user.models import User
from django.utils.translation import gettext as _
from django.contrib.messages import get_messages


class FeedbackViewTestCase(TestCase):
    fixtures = [
        "tests/fixtures/test_teams.json",
        "tests/fixtures/test_users.json"
    ]

    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(username='he')
        self.url = reverse('feedback')

    def test_feedback_view_redirect_for_unauthorized_user(self):
        """Test that unauthorized user is redirected to login."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('login'))

    def test_feedback_view_message_for_unauthorized_user(self):
        """Test that unauthorized user sees error message."""
        response = self.client.get(self.url, follow=True)
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        msg = _("You are not authorized! Please login.")
        self.assertEqual(str(messages[0]), msg)

    def test_feedback_view_status_code_for_authorized_user(self):
        """Test that authorized user can access feedback page."""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_feedback_view_template_used(self):
        """Test that correct template is used."""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'feedback.html')

    def test_feedback_view_contains_form_fields(self):
        """Test that feedback page contains all required form fields."""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, _("Specify the subject:"))
        contact_label = _("* Your email or Telegram (@username):")
        self.assertContains(response, contact_label)
        self.assertContains(response, _("* Message:"))
        self.assertContains(response, _("Send"))

    def test_feedback_view_contains_title(self):
        """Test that feedback page contains title."""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, _("Feedback"))

    def test_feedback_view_contains_description(self):
        """Test that feedback page contains description text."""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        desc = _("Found a bug or have a suggestion? Let us know!")
        self.assertContains(response, desc)

    def test_feedback_view_note_about_telegram(self):
        """Test that feedback page contains note about Telegram."""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, _("Note"))
        note = _("Your message will be sent to developers via Telegram. "
                 "We will reply to the contact you provide.")
        self.assertContains(response, note)


class FeedbackSendTestCase(TestCase):
    """Server-side feedback sending via Telegram Bot API."""

    fixtures = [
        "tests/fixtures/test_teams.json",
        "tests/fixtures/test_users.json"
    ]

    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(username='he')
        self.client.force_login(self.user)
        self.url = reverse('feedback')
        self.payload = {
            'subject': 'Bug',
            'contact': '@tester',
            'message': 'Something is broken',
        }
        # Reset the in-memory throttle between tests
        from task_manager import views
        views._feedback_last_sent.clear()

    @patch('task_manager.views.send_feedback_to_telegram')
    def test_send_success(self, mock_send):
        mock_send.return_value = (True, None)
        response = self.client.post(self.url, self.payload)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])
        mock_send.assert_called_once()
        sent_text = mock_send.call_args[0][0]
        self.assertIn('Bug', sent_text)
        self.assertIn('@tester', sent_text)
        self.assertIn('Something is broken', sent_text)

    @patch('task_manager.views.send_feedback_to_telegram')
    def test_send_telegram_failure(self, mock_send):
        mock_send.return_value = (False, 'error')
        response = self.client.post(self.url, self.payload)
        self.assertEqual(response.status_code, 502)
        self.assertFalse(response.json()['ok'])

    def test_send_invalid_form(self):
        response = self.client.post(self.url, {'subject': ''})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['ok'])

    @patch('task_manager.views.send_feedback_to_telegram')
    def test_send_throttled(self, mock_send):
        mock_send.return_value = (True, None)
        first = self.client.post(self.url, self.payload)
        self.assertEqual(first.status_code, 200)
        second = self.client.post(self.url, self.payload)
        self.assertEqual(second.status_code, 429)
        self.assertFalse(second.json()['ok'])
        # Only the first message actually reached Telegram
        self.assertEqual(mock_send.call_count, 1)

    def test_send_unauthorized(self):
        self.client.logout()
        response = self.client.post(self.url, self.payload)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('login'))

    @patch.dict(os.environ, {'TELEGRAM_BOT_TOKEN': '',
                             'TELEGRAM_CHAT_ID': ''})
    def test_send_not_configured(self):
        from task_manager.telegram import (
            send_feedback_to_telegram, is_telegram_feedback_configured
        )
        self.assertFalse(is_telegram_feedback_configured())
        sent, error = send_feedback_to_telegram('text')
        self.assertFalse(sent)


class TelegramModuleTestCase(TestCase):

    def test_send_success(self):
        with patch.dict(os.environ,
                        {'TELEGRAM_BOT_TOKEN': 'token',
                         'TELEGRAM_CHAT_ID': '123'}):
            with patch('urllib.request.urlopen') as mock_urlopen:
                mock_resp = MagicMock()
                mock_resp.read.return_value = b'{"ok": true}'
                mock_resp.__enter__.return_value = mock_resp
                mock_urlopen.return_value = mock_resp
                from task_manager.telegram import (
                    send_feedback_to_telegram
                )
                sent, error = send_feedback_to_telegram('hello')
                self.assertTrue(sent)
                self.assertIsNone(error)
                request = mock_urlopen.call_args[0][0]
                self.assertIn('bottoken/sendMessage', request.full_url)

    def test_send_network_error(self):
        with patch.dict(os.environ,
                        {'TELEGRAM_BOT_TOKEN': 'token',
                         'TELEGRAM_CHAT_ID': '123'}):
            with patch('urllib.request.urlopen',
                       side_effect=urllib.error.URLError('boom')):
                from task_manager.telegram import (
                    send_feedback_to_telegram
                )
                sent, error = send_feedback_to_telegram('hello')
                self.assertFalse(sent)
                self.assertIsNotNone(error)
