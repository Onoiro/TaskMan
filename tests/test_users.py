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

    def test_create_user_response_200(self):
        response = self.c.post(reverse('user:user-create'), self.user_data, follow=True)
        self.assertEqual(response.status_code, 200)
    

    def test_created_user_add_to_db(self):
        old_count = User.objects.count()
        self.c.post(reverse('user:user-create'), self.user_data, follow=True)
        new_count = User.objects.count()
        self.assertEqual(old_count + 1, new_count)


    def test_check_for_not_create_user_with_same_username(self):
        self.c.post(reverse('user:user-create'), self.user_data, follow=True)
        users_count = User.objects.count()
        self.c.post(reverse('user:user-create'), self.user_data, follow=True)
        new_users_count = User.objects.count()
        self.assertEqual(users_count, new_users_count)

    
    def test_create_user_with_correct_data(self):
        self.c.post(reverse('user:user-create'), self.user_data, follow=True)
        user = User.objects.filter(username=self.user_data['username']).first()
        self.assertEqual(user.first_name, self.user_data['first_name'])
        self.assertEqual(user.last_name, self.user_data['last_name'])


    def test_update_user(self):
        self.c.post(reverse('user:user-create'), self.user_data, follow=True)
        user = User.objects.get(username=self.user_data['username'])
        self.c.force_login(user)
        new_user_data = {
            'first_name': 'new_first_name',
            'last_name': 'new_last_name',
            'username': 'new_username',
            'password1': 222,
            'password2': 222,
        }
        response = self.c.post(reverse('user:user-update', args=[user.id]), new_user_data, follow=True)
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.first_name, new_user_data['first_name'])
        self.assertEqual(user.last_name, new_user_data['last_name'])
