from django.test import TestCase, Client
from django.urls import reverse
# from django.contrib.auth.models import User
from task_manager.user.models import User
from django.utils.translation import gettext as _
from django.contrib.messages import get_messages


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
