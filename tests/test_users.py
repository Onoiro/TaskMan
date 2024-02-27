import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "task_manager.settings")

import django
django.setup()

from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse
from django.core.management import call_command


class UserTestCase(TestCase):

    # fixtures = ['new_test_user.json']

    # @classmethod
    # def setUpTestData(cls):
    #     print("setUpTestData: Run once to set up non-modified data for all class methods.")

    def setUp(self):
        self.c = Client()
        # call_command('loaddata', 'new_test_user.json')
        self.user_data = {
                    'first_name': 'Me',
                    'last_name': 'M',
                    'username': 'me',
                    'password': 111,
                    # 'password2': 'test_password2'
            }

    def test_create_user(self):
        old_count = User.objects.count()
        response = self.c.post(reverse('user:user-create'), self.user_data, follow=True)
        self.assertEqual(response.status_code, 200)
        new_count = User.objects.count()
        self.assertEqual(old_count + 1, new_count)
        # user = User.objects.filter(username=self.user_data["fields"]["username"]).first()
        # self.assertIsNotNone(user)
        # self.assertEqual(user.first_name, self.user_data['first_name'])
        # self.assertEqual(user.last_name, self.user_data['last_name'])
