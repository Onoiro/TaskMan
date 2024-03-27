from task_manager.statuses.models import Statuses
# from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse


class StatusesTestCase(TestCase):
    fixtures = ["tests/fixtures/test_users.json"]

    def setUp(self):
        self.c = Client()
        self.statuses_data = {
            'name': 'test_status',
        }

    def test_create_status_response_200(self):
        response = self.c.post(reverse('statuses:statuses-create'),
                               self.statuses_data, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_created_status_add_to_db(self):
        old_count = Statuses.objects.count()
        self.c.post(reverse('statuses:statuses-create'), self.statuses_data, follow=True)
        new_count = Statuses.objects.count()
        self.assertEqual(old_count + 1, new_count)

    def test_check_for_not_create_status_with_same_name(self):
        self.c.post(reverse('statuses:statuses-create'), self.statuses_data, follow=True)
        statuses_count = Statuses.objects.count()
        self.c.post(reverse('statuses:statuses-create'), self.statuses_data, follow=True)
        new_statuses_count = Statuses.objects.count()
        self.assertEqual(statuses_count, new_statuses_count)

    def test_create_status_with_correct_data(self):
        self.c.post(reverse('statuses:statuses-create'), self.statuses_data, follow=True)
        status = Statuses.objects.filter(name=self.statuses_data['name']).first()
        self.assertEqual(status.name, self.statuses_data['name'])

    # def test_update_status(self):
    #     user = User.objects.get(username="he")
    #     self.c.force_login(user)
    #     status = Statuses.objects.get(name="test_status")
    #     new_status_data = {
    #         'name': 'new_test_status'
    #     }
    #     response = self.c.post(
    #         reverse('statuses:statuses-update', args=[status.id]),
    #         new_status_data,
    #         follow=True)
    #     self.assertEqual(response.status_code, 200)
    #     status.refresh_from_db()
    #     self.assertEqual(status.name, new_status_data['name'])

    # def test_delete_user(self):
    #     user = User.objects.get(username="he")
    #     self.c.force_login(user)
    #     self.c.post(reverse('user:user-delete', args=[user.id]), follow=True)
    #     self.assertFalse(User.objects.filter(username="he").exists())
