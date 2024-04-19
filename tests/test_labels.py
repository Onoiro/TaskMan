from task_manager.labels.models import Label
from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse


class LabelsTestCase(TestCase):
    fixtures = ["tests/fixtures/test_users.json",
                # "tests/fixtures/test_statuses.json",
                # "tests/fixtures/test_tasks.json",
                "tests/fixtures/test_labels.json"]

    def setUp(self):
        self.user = User.objects.get(username='me')
        self.c = Client()
        self.c.force_login(self.user)
        self.labels_data = {
            'name': 'new_test_label',
        }

    def test_create_label_response_200(self):
        response = self.c.post(reverse('labels:labels-create'),
                               self.labels_data, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_created_label_add_to_db(self):
        old_count = Label.objects.count()
        self.c.post(reverse('labels:labels-create'),
                    self.labels_data, follow=True)
        new_count = Label.objects.count()
        self.assertEqual(old_count + 1, new_count)

    def test_check_for_not_create_label_with_same_name(self):
        self.c.post(reverse('labels:labels-create'),
                    self.labels_data, follow=True)
        labels_count = Label.objects.count()
        self.c.post(reverse('labels:labels-create'),
                    self.labels_data, follow=True)
        new_labels_count = Label.objects.count()
        self.assertEqual(labels_count, new_labels_count)

    def test_create_label_with_correct_data(self):
        self.c.post(reverse('labels:labels-create'),
                    self.labels_data, follow=True)
        label = Label.objects.filter(
            name=self.labels_data['name']).first()
        self.assertEqual(label.name, self.labels_data['name'])

    def test_update_label(self):
        label = Label.objects.get(name="bug")
        response = self.c.post(
            reverse('labels:labels-update', args=[label.id]),
            self.labels_data,
            follow=True)
        self.assertEqual(response.status_code, 200)
        label.refresh_from_db()
        self.assertEqual(label.name, self.labels_data['name'])

    def test_delete_label(self):
        label = Label.objects.get(name="bug")
        self.c.post(reverse('labels:labels-delete',
                            args=[label.id]), follow=True)
        self.assertFalse(Label.objects.filter(name="bug").exists())

    # def add_labels_to_task(self):
    #     task = Task.objects.get(name="first_task")
