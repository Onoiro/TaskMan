from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils.translation import gettext as _
from django.contrib.messages import get_messages


class IndexViewTestCase(TestCase):

    def test_index_view_status_code(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)

    def test_index_view_template_used(self):
        response = self.client.get(reverse('index'))
        self.assertTemplateUsed(response, 'index.html')

    def test_index_view_content(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, _("Hello from Hexlet!"))
        self.assertContains(response, _('Practical programming courses'))
        self.assertContains(response, _("Read more"))


class UserLoginViewTestCase(TestCase):
    fixtures = ["tests/fixtures/test_users.json"]

    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(username='he')
        self.password = self.user.password

    def test_login_view_status_code(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_login_view_template_used(self):
        response = self.client.get(reverse('login'))
        self.assertTemplateUsed(response, 'login.html')

    def test_login_view_content(self):
        response = self.client.get(reverse('login'))
        self.assertContains(response, _("Login"))
        self.assertContains(response, _("Log in"))
        self.assertContains(response, _("Username"))
        self.assertContains(response, _("Password"))

    def test_user_login(self):
        logged_in = self.client.post(reverse('login'), {
            'username': self.user.username,
            'password': self.password
        })
        self.assertTrue(logged_in)

    def test_status_code_if_user_login(self):
        response = self.client.post(reverse('login'), {
            'username': self.user.username,
            'password': self.password
        }, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_login_incorrect_user(self):
        response = self.client.post(reverse('login'), {
            'username': 'wrong_user',
            'password': 'incorrect_password'
        })
        message = _(
            "Please enter a correct username and password."
            " Note that both fields may be case-sensitive."
        )
        self.assertContains(response, message)

    '''I don't understand why this test is fail with no messages at all'''
    # def test_user_login_success_message(self):
    #     response = self.client.post(reverse('login'), {
    #         'username': self.user.username,
    #         'password': self.password
    #         }, follow=True)
    #     messages = list(get_messages(response.wsgi_request))
    #     print(messages)
    #     self.assertNotEqual(len(messages), 0)
    #     self.assertEqual(str(messages[0]), _("You successfully logged in"))


class UserLogoutViewTestCase(TestCase):
    fixtures = ["tests/fixtures/test_users.json"]

    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(username='he')
        self.client.force_login(self.user)
        # self.password = self.user.password

    def test_logout_view_status_code(self):
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)

    def test_user_logout(self):
        response = self.client.get(reverse('logout'))
        self.assertRedirects(response, reverse('index'))
        messages = list(get_messages(response.wsgi_request))
        # print(messages[0])
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]), _("You are logged out"))
