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
