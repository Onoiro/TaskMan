from django.test import TestCase, Client
from django.urls import reverse
# from django.contrib.auth.models import User
from task_manager.user.models import User
from django.contrib.messages import get_messages
from django.utils.translation import gettext as _


class PermissionsTestCase(TestCase):
    fixtures = ["tests/fixtures/test_users.json",
                "tests/fixtures/test_tasks.json",
                "tests/fixtures/test_statuses.json",
                "tests/fixtures/test_labels.json"]

    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(username='me')
        self.he = User.objects.get(username='he')

    def test_custom_permissions_redirect_unauthenticated_user(self):
        response = self.client.get(reverse(
            'user:user-update', args=[self.he.id]), follow=True)
        self.assertRedirects(response, reverse('login'))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]),
                         _('You are not authorized! Please login.'))

    def test_user_permissions_can_not_modifying_other_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse(
            'user:user-update', args=[self.he.id]), follow=True)
        self.assertRedirects(response, reverse('user:user-list'))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(
            str(messages[0]),
            _("You don't have permissions to modify another user."))
