from task_manager.statuses.models import Status
from task_manager.user.models import User
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.messages import get_messages
from django.utils.translation import gettext as _


class StatusesTestCase(TestCase):
    fixtures = ["tests/fixtures/test_users.json",
                "tests/fixtures/test_teams.json",
                "tests/fixtures/test_teams_memberships.json",
                "tests/fixtures/test_tasks.json",
                "tests/fixtures/test_statuses.json",
                "tests/fixtures/test_labels.json"]

    def setUp(self):
        self.user = User.objects.get(username='me')
        self.c = Client()
        self.c.force_login(self.user)
        self.statuses_data = {
            'name': 'new_test_status',
            'description': 'Test description'
        }

    # list

    def test_statuses_list_response_200(self):
        response = self.c.get(reverse('statuses:statuses-list'))
        self.assertEqual(response.status_code, 200)

    def test_statuses_list_static_content(self):
        response = self.c.get(reverse('statuses:statuses-list'))
        self.assertContains(response, 'ID')
        self.assertContains(response, _('Name'))
        self.assertContains(response, _('Description'))
        self.assertContains(response, _('Created at'))
        self.assertContains(response, _('Statuses'))
        self.assertContains(response, _('New status'))

    def test_statuses_list_has_tasks_button(self):
        response = self.c.get(reverse('statuses:statuses-list'))
        self.assertContains(response, _("Tasks"))
        self.assertContains(response, reverse('tasks:tasks-list'))

    def test_statuses_list_has_labels_button(self):
        response = self.c.get(reverse('statuses:statuses-list'))
        self.assertContains(response, _("Labels"))
        self.assertContains(response, reverse('labels:labels-list'))

    def test_statuses_list_content(self):
        response = self.c.get(reverse('statuses:statuses-list'))
        team_user_ids = User.objects.filter(
            team=self.user.team).values_list('pk', flat=True)
        statuses = Status.objects.filter(creator__in=team_user_ids)
        for status in statuses:
            self.assertContains(response, status.name)
        other_statuses = Status.objects.exclude(creator__in=team_user_ids)
        for status in other_statuses:
            self.assertNotContains(response, status.name)

    def test_statuses_list_empty_description(self):
        response = self.c.get(reverse('statuses:statuses-list'))
        Status.objects.get(name="testing")  # status with empty description
        Status.objects.get(name="finished")  # status with null description
        self.assertNotContains(response, "None")
        self.assertContains(response, "Newly created task")

    def test_create_status_with_description(self):
        self.c.post(
            reverse('statuses:statuses-create'),
            self.statuses_data,
            follow=True
        )
        status = Status.objects.filter(
            name=self.statuses_data['name']).first()
        self.assertEqual(
            status.description, self.statuses_data['description'])

    def test_update_status_description(self):
        status = Status.objects.get(name="new")
        new_data = {
            'name': 'updated',
            'description': 'Updated description'
        }
        self.c.post(reverse('statuses:statuses-update', args=[status.id]),
                    new_data, follow=True)
        status.refresh_from_db()
        self.assertEqual(
            status.description, new_data['description'])

    def test_create_status_without_description(self):
        data_without_desc = {'name': 'no_desc_status'}
        self.c.post(reverse('statuses:statuses-create'),
                    data_without_desc, follow=True)
        status = Status.objects.filter(
            name=data_without_desc['name']).first()
        self.assertEqual(status.description, '')

    # create

    def test_get_create_status_response_200_and_check_content(self):
        response = self.c.get(reverse('statuses:statuses-create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, _('Name'))
        self.assertContains(response, _('Create'))
        self.assertRegex(
            response.content.decode('utf-8'),
            _(r'\bCreate status\b'))

    def test_create_status_response_200(self):
        response = self.c.post(reverse('statuses:statuses-create'),
                               self.statuses_data, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_created_status_add_to_db(self):
        old_count = Status.objects.count()
        self.c.post(reverse('statuses:statuses-create'),
                    self.statuses_data, follow=True)
        new_count = Status.objects.count()
        self.assertEqual(old_count + 1, new_count)

    def test_create_status_with_correct_data(self):
        response = self.c.post(reverse('statuses:statuses-create'),
                               self.statuses_data, follow=True)
        status = Status.objects.filter(
            name=self.statuses_data['name']).first()
        self.assertEqual(status.name, self.statuses_data['name'])
        self.assertRedirects(response, reverse('statuses:statuses-list'))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]), _('Status created successfully'))

    def test_can_not_create_status_with_empty_name(self):
        self.statuses_data = {'name': ' '}
        response = self.c.post(reverse('statuses:statuses-create'),
                               self.statuses_data, follow=True)
        self.assertFalse(Status.objects.filter(name=" ").exists())
        message = _('This field is required.')
        self.assertContains(response, message)

    # update

    def test_get_update_status_response_200_and_check_content(self):
        status = Status.objects.get(name="new")
        response = self.c.get(reverse('statuses:statuses-update',
                              args=[status.id]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, _('Name'))
        self.assertContains(response, _('Edit'))
        self.assertContains(response, _('new'))
        self.assertRegex(
            response.content.decode('utf-8'),
            _(r'\bEdit status\b')
        )

    def test_update_status_successfully(self):
        status = Status.objects.get(name="new")
        response = self.c.post(
            reverse('statuses:statuses-update', args=[status.id]),
            self.statuses_data, follow=True)
        status.refresh_from_db()
        self.assertEqual(status.name, self.statuses_data['name'])
        self.assertRedirects(response, reverse('statuses:statuses-list'))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]), _('Status updated successfully'))

    def test_can_not_set_empty_name_when_update_status(self):
        status = Status.objects.get(name="new")
        self.statuses_data = {'name': ' '}
        response = self.c.post(
            reverse('statuses:statuses-update', args=[status.id]),
            self.statuses_data, follow=True)
        self.assertFalse(Status.objects.filter(name=" ").exists())
        message = _('This field is required.')
        self.assertContains(response, message)

    # delete

    def test_get_delete_status_response_200_and_check_content(self):
        status = Status.objects.get(name="new")
        response = self.c.get(
            reverse('statuses:statuses-delete',
                    args=[status.id]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, _('Delete status'))
        self.assertContains(response, _('Yes, delete'))
        self.assertContains(response,
                            _('Are you sure you want to delete new?'))

    def test_delete_status_successfully(self):
        status = Status.objects.get(name="testing")
        response = self.c.post(
            reverse('statuses:statuses-delete',
                    args=[status.id]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Status.objects.filter(name="testing").exists())
        self.assertRedirects(response, reverse('statuses:statuses-list'))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]),
                         _('Status deleted successfully'))

    def test_can_not_delete_status_bound_with_task(self):
        status = Status.objects.get(name="new")
        response = self.c.post(
            reverse('statuses:statuses-delete',
                    args=[status.id]), follow=True)
        self.assertTrue(Status.objects.filter(name="new").exists())
        self.assertRedirects(response, reverse('statuses:statuses-list'))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]),
                         _('Cannot delete status because it is in use'))


class StatusDefaultCreationTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='test_user',
            password='testpass123'
        )

    def test_create_default_statuses_for_user(self):
        default_status_names = [
            "To Do",
            "In Progress",
            "On Hold",
            "Completed",
            "Cancelled",
            "Blocked"
        ]

        # initially no statuses for user
        self.assertEqual(Status.objects.filter(creator=self.user).count(), 0)

        # create default statuses
        created_statuses = Status.create_default_statuses_for_user(self.user)

        # check correct number of statuses created
        self.assertEqual(len(created_statuses), 6)
        self.assertEqual(Status.objects.filter(creator=self.user).count(), 6)

        # check all default statuses exist with correct names
        for status_name in default_status_names:
            self.assertTrue(
                Status.objects.filter(
                    name=status_name,
                    creator=self.user
                ).exists()
            )

        # check descriptions are not empty
        for status in created_statuses:
            self.assertTrue(status.description)
