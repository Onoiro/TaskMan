import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "task_manager.settings")

import django
django.setup()

from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse


class UserTestCase(TestCase):

    def setUp(self):
        self.c = Client()
        self.user_data = {
                    'first_name': 'Me',
                    'last_name': 'M',
                    'username': 'me',
                    'password1': 111,
                    'password2': 111,
            }

    def test_create_user(self):
        old_count = User.objects.count()
        response = self.c.post(reverse('user:user-create'), self.user_data, follow=True)
        self.assertEqual(response.status_code, 200)
        new_count = User.objects.count()
        self.assertEqual(old_count + 1, new_count)
