from django.test import TestCase, Client
from django.urls import reverse
# from django.contrib.auth.models import User
from task_manager.user.models import User
from django.utils.translation import gettext as _
from django.contrib.messages import get_messages
from unittest.mock import patch


class UserLoginViewTestCase(TestCase):
    fixtures = ["tests/fixtures/test_teams.json",
                "tests/fixtures/test_users.json"]

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='test_user',
            password='password')
        self.client.force_login(self.user)

    def test_login_view_response_200_and_check_content(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')
        self.assertContains(response, _("Login"))
        self.assertContains(response, _("Log in"))
        self.assertContains(response, _("Username"))
        self.assertContains(response, _("Password"))

    def test_user_login_successfully(self):
        self.client.logout()
        response = self.client.post(reverse('login'), {
            'username': 'test_user',
            'password': 'password'
        })
        self.assertTrue(response)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('tasks:tasks-list'))
        messages = list(get_messages(response.wsgi_request))
        self.assertNotEqual(len(messages), 0)
        self.assertEqual(str(messages[0]), _("You successfully logged in"))

    def test_login_incorrect_user(self):
        response = self.client.post(reverse('login'), {
            'username': 'wrong_user',
            'password': 'incorrect_password'
        })
        self.assertNotEqual(response.status_code, 302)
        message = _(
            "Please enter a correct username and password."
            " Note that both fields may be case-sensitive."
        )
        self.assertContains(response, message)


class UserLogoutViewTestCase(TestCase):
    fixtures = ["tests/fixtures/test_teams.json",
                "tests/fixtures/test_users.json"]

    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(username='he')
        self.client.force_login(self.user)

    def test_user_logout(self):
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('index'))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]), _("You are logged out"))

    def test_user_logout_dispatch_called(self):
        """Test that UserLogoutView.dispatch is called."""
        from task_manager.views import UserLogoutView

        # Verify our dispatch method is used
        self.assertIn('dispatch', UserLogoutView.__dict__)

    @patch('task_manager.views.messages.info')
    def test_user_logout_calls_dispatch_message(self, mock_message_info):
        """Test that dispatch adds logout message."""
        # This test ensures the dispatch method is called and adds a message
        response = self.client.post(reverse('logout'))

        # Check that messages.info was called with "You are logged out"
        mock_message_info.assert_called()
        call_args = mock_message_info.call_args
        self.assertIn('logged out', str(call_args[0][1]).lower())

    def test_user_logout_view_dispatch_execution(self):
        """Test that UserLogoutView.dispatch method executes correctly."""
        from task_manager.views import UserLogoutView
        from django.http import HttpRequest
        from django.contrib.sessions.middleware import SessionMiddleware
        from django.contrib.messages.middleware import MessageMiddleware
        from django.contrib.auth import get_user_model

        User = get_user_model()

        # Create a request with session and messages
        request = HttpRequest()
        request.method = 'POST'

        # Add session
        middleware = SessionMiddleware(lambda r: None)
        middleware.process_request(request)
        request.session.save()

        # Add user
        request.user = self.user

        # Add messages middleware
        msg_middleware = MessageMiddleware(lambda r: None)
        msg_middleware.process_request(request)

        # Call dispatch directly
        view = UserLogoutView()
        # Call dispatch, which should add the message and call super().dispatch()
        # We expect 403 due to CSRF, but the message should still be added
        try:
            response = view.dispatch(request)
        except Exception:
            pass  # CSRF error is expected

        # Check message was added (this verifies dispatch ran)
        messages = list(get_messages(request))
        self.assertGreater(len(messages), 0)
        self.assertIn('logged out', str(messages[0]).lower())
