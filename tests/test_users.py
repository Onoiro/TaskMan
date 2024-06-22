# import os
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "task_manager.settings")

# import django
# django.setup()

from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.messages import get_messages
from django.utils.translation import gettext as _


class UserTestCase(TestCase):
    fixtures = ["tests/fixtures/test_users.json"]

    def setUp(self):
        self.c = Client()
        self.user_data = {
            'first_name': 'New',
            'last_name': 'N',
            'username': 'new',
            'password1': 111,
            'password2': 111,
        }
    
    # list

    def test_user_list_response_200(self):
        response = self.c.get(reverse('user:user-list'))
        self.assertEqual(response.status_code, 200)

    def test_user_list_content(self):
        response = self.c.get(reverse('user:user-list'))
        self.assertContains(response, 'ID')
        self.assertContains(response, _('User name'))
        self.assertContains(response, _('Fullname'))
        self.assertContains(response, _('Created at'))
        self.assertContains(response, _('Users'))

    # create

    def test_create_user_response_200(self):
        response = self.c.post(reverse('user:user-create'),
                               self.user_data, follow=True)
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

    # update

    def test_update_user(self):
        user = User.objects.get(username="he")
        self.c.force_login(user)
        new_user_data = {
            'first_name': 'He',
            'last_name': 'H',
            'username': 'him',
            'password1': 222,
            'password2': 222
        }
        response = self.c.post(
            reverse('user:user-update', args=[user.id]),
            new_user_data,
            follow=True)
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.username, new_user_data['username'])

    # delete

    def test_delete_user(self):
        user = User.objects.get(username="he")
        self.c.force_login(user)
        response = self.c.post(reverse('user:user-delete',
                                       args=[user.id]), follow=True)
        self.assertFalse(User.objects.filter(username="he").exists())
        self.assertEqual(response.status_code, 200)
