from task_manager.labels.models import Label
from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.messages import get_messages
from django.utils.translation import gettext as _


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

    def test_labels_list_response_200(self):
        response = self.c.get(reverse('labels:labels-list'))
        self.assertEqual(response.status_code, 200)

    def test_labels_list_content(self):
        response = self.c.get(reverse('labels:labels-list'))
        self.assertContains(response, 'ID')
        self.assertContains(response, _('Name'))
        self.assertContains(response, _('Created at'))

    def test_create_label_response_200(self):
        response = self.c.post(reverse('labels:labels-create'),
                               self.labels_data, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_create_label_content(self):
        response = self.c.get(reverse('labels:labels-create'))
        self.assertContains(response, _('Name'))
        self.assertContains(response, _('Create label'))
        self.assertContains(response, _('Create'))

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

    def test_check_message_if_same_label_exist(self):
        self.labels_data = {'name': 'bug'}
        response = self.c.post(reverse('labels:labels-create'),
                               self.labels_data, follow=True)
        message = _('Label with this Name already exists.')
        self.assertContains(response, message)

    def test_create_label_with_correct_data(self):
        self.c.post(reverse('labels:labels-create'),
                    self.labels_data, follow=True)
        label = Label.objects.filter(
            name=self.labels_data['name']).first()
        self.assertEqual(label.name, self.labels_data['name'])

    def test_success_redirect_when_create_label(self):
        response = self.c.post(reverse('labels:labels-create'),
                               self.labels_data, follow=True)
        self.assertRedirects(response, reverse('labels:labels-list'))

    def test_get_success_message_when_create_label(self):
        response = self.c.post(reverse('labels:labels-create'),
                               self.labels_data, follow=True)
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]), _('Label created successfully'))

    def test_update_label_response_200(self):
        label = Label.objects.get(name="bug")
        response = self.c.post(
            reverse('labels:labels-update', args=[label.id]),
            self.labels_data,
            follow=True)
        self.assertEqual(response.status_code, 200)

    def test_update_label_content(self):
        label = Label.objects.get(name="bug")
        response = self.c.get(
            reverse('labels:labels-update', args=[label.id]),
            self.labels_data,
            follow=True)
        self.assertContains(response, _('Name'))
        self.assertContains(response, _('Edit label'))
        self.assertContains(response, _('Edit'))
        self.assertContains(response, _('bug'))

    def test_updated_label_update_in_db(self):
        label = Label.objects.get(name="bug")
        self.c.post(reverse('labels:labels-update', args=[label.id]),
                    self.labels_data, follow=True)
        label.refresh_from_db()
        self.assertEqual(label.name, self.labels_data['name'])

    def test_get_success_message_when_update_label(self):
        label = Label.objects.get(name="bug")
        response = self.c.post(
            reverse('labels:labels-update', args=[label.id]),
            self.labels_data, follow=True)
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]), _('Label updated successfully'))

    def test_check_can_not_update_label_if_same_label_exist(self):
        label = Label.objects.get(name="feature")
        self.labels_data = {'name': 'bug'}
        response = self.c.post(
            reverse('labels:labels-update', args=[label.id]),
            self.labels_data, follow=True
        )
        message = _('Label with this Name already exists.')
        self.assertContains(response, message)

    def test_no_redirect_when_not_update_label(self):
        label = Label.objects.get(name="feature")
        self.labels_data = {'name': 'bug'}
        response = self.c.post(
            reverse('labels:labels-update', args=[label.id]),
            self.labels_data, follow=True
        )
        self.assertNotEqual(response.status_code, 302)

    def test_delete_label_response_200(self):
        label = Label.objects.get(name="bug")
        response = self.c.post(reverse('labels:labels-delete',
                               args=[label.id]), follow=True)
        self.assertEqual(response.status_code, 200)

    def test_delete_label_content(self):
        label = Label.objects.get(name="bug")
        response = self.c.get(reverse('labels:labels-delete',
                              args=[label.id]), follow=True)
        self.assertContains(response, _('Delete label'))
        self.assertContains(response, _('Yes, delete'))
        self.assertContains(response, _('Are you sure you want to delete bug?'))

    def test_delete_label(self):
        label = Label.objects.get(name="bug")
        self.c.post(reverse('labels:labels-delete',
                            args=[label.id]), follow=True)
        self.assertFalse(Label.objects.filter(name="bug").exists())

    def test_check_message_when_delete_label(self):
        label = Label.objects.get(name="bug")
        response = self.c.post(
            reverse('labels:labels-delete', args=[label.id]),
            self.labels_data, follow=True)
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]), _('Label deleted successfully'))

    # have to test if delete label is bound to some task
    # def add_labels_to_task(self):
    #     task = Task.objects.get(name="first_task")
