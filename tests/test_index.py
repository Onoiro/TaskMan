from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils.translation import gettext as _
from django.contrib.messages import get_messages


class IndexViewTests(TestCase):

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


# class UserLoginViewTests(TestCase):

#     def setUp(self):
#         self.client = Client()
#         self.user = User.objects.create_user(username='testuser', password='12345')

#     def test_login_view_status_code(self):
#         response = self.client.get(reverse('login'))
#         self.assertEqual(response.status_code, 200)

#     def test_login_view_template_used(self):
#         response = self.client.get(reverse('login'))
#         self.assertTemplateUsed(response, 'login.html')

#     def test_user_login(self):
#         response = self.client.post(reverse('login'), {
#             'username': 'testuser',
#             'password': '12345'
#         })
#         self.assertRedirects(response, reverse('index'))
#         messages = list(get_messages(response.wsgi_request))
#         self.assertGreater(len(messages), 0)
#         self.assertEqual(str(messages[0]), _("You successfully logged in"))


# class UserLogoutViewTests(TestCase):

#     def setUp(self):
#         self.client = Client()
#         self.user = User.objects.create_user(username='testuser', password='12345')
#         self.client.login(username='testuser', password='12345')

#     def test_logout_view_status_code(self):
#         response = self.client.get(reverse('logout'))
#         self.assertEqual(response.status_code, 302)

#     def test_user_logout(self):
#         response = self.client.get(reverse('logout'))
#         self.assertRedirects(response, reverse('index'))
#         messages = list(get_messages(response.wsgi_request))
#         self.assertGreater(len(messages), 0)
#         self.assertEqual(str(messages[0]), _("You are logged out"))