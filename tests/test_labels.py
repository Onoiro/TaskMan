from task_manager.labels.models import Label
from task_manager.user.models import User
from task_manager.teams.models import TeamMembership
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.messages import get_messages
from django.utils.translation import gettext as _
from django.utils.dateformat import DateFormat
from django.utils.formats import get_format


class LabelsTestCase(TestCase):
    fixtures = ["tests/fixtures/test_users.json",
                "tests/fixtures/test_teams.json",
                "tests/fixtures/test_teams_memberships.json",
                "tests/fixtures/test_statuses.json",
                "tests/fixtures/test_tasks.json",
                "tests/fixtures/test_labels.json"]

    def setUp(self):
        self.user = User.objects.get(username='me')
        self.c = Client()
        self.c.force_login(self.user)
        self.labels_data = {'name': 'new_test_label'}

    # list

    def test_labels_list_response_200(self):
        response = self.c.get(reverse('labels:labels-list'))
        self.assertEqual(response.status_code, 200)

    def test_labels_list_static_content(self):
        response = self.c.get(reverse('labels:labels-list'))
        self.assertContains(response, 'ID')
        self.assertContains(response, _('Name'))
        self.assertContains(response, _('Created at'))
        self.assertContains(response, _('Labels'))
        self.assertContains(response, _('New label'))
        # Check for Edit and Delete links in the table rows, not as standalone text
        labels = self._get_user_team_labels()
        if labels.exists():
            # Edit and Delete buttons appear only if there are labels
            self.assertContains(response, reverse('labels:labels-update', args=[labels.first().id]))
            self.assertContains(response, reverse('labels:labels-delete', args=[labels.first().id]))

    def test_labels_list_has_tasks_button(self):
        response = self.c.get(reverse('labels:labels-list'))
        self.assertContains(response, _("Tasks"))
        self.assertContains(response, reverse('tasks:tasks-list'))

    def test_labels_list_has_statuses_button(self):
        response = self.c.get(reverse('labels:labels-list'))
        self.assertContains(response, _("Statuses"))
        self.assertContains(response, reverse('statuses:statuses-list'))

    def test_labels_list_content(self):
        response = self.c.get(reverse('labels:labels-list'))
        
        # Get user's teams
        user_teams = TeamMembership.objects.filter(
            user=self.user
        ).values_list('team', flat=True)
        
        # Get all users in the same teams
        team_user_ids = TeamMembership.objects.filter(
            team__in=user_teams
        ).values_list('user', flat=True).distinct()
        
        # For users without teams, show only their own labels
        if not team_user_ids:
            team_user_ids = [self.user.id]
        
        labels = Label.objects.filter(creator__in=team_user_ids)
        for label in labels:
            self.assertContains(response, label.name)
            formatted_date = DateFormat(
                label.created_at).format(get_format('DATETIME_FORMAT'))
            self.assertContains(response, formatted_date)
            
        other_labels = Label.objects.exclude(creator__in=team_user_ids)
        for label in other_labels:
            self.assertNotContains(response, label.name)

    def _get_user_team_labels(self):
        """Helper method to get labels visible to user"""
        # Get user's teams
        user_teams = TeamMembership.objects.filter(
            user=self.user
        ).values_list('team', flat=True)
        
        # Get all users in the same teams
        team_user_ids = TeamMembership.objects.filter(
            team__in=user_teams
        ).values_list('user', flat=True).distinct()
        
        # For users without teams, show only their own labels
        if not team_user_ids:
            team_user_ids = [self.user.id]
            
        return Label.objects.filter(creator__in=team_user_ids)

    # create

    def test_get_create_label_response_200_check_content(self):
        response = self.c.get(reverse('labels:labels-create'),
                              self.labels_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, _('Name'))
        self.assertContains(response, _('Create'))
        self.assertRegex(
            response.content.decode('utf-8'),
            _(r'\bCreate label\b'))

    def test_post_create_label_response_200(self):
        response = self.c.post(reverse('labels:labels-create'),
                               self.labels_data, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_create_label_successfully(self):
        old_count = Label.objects.count()
        response = self.c.post(
            reverse('labels:labels-create'),
            self.labels_data, follow=True)
        new_count = Label.objects.count()
        self.assertEqual(old_count + 1, new_count)
        label = Label.objects.filter(
            name=self.labels_data['name']).first()
        self.assertEqual(label.name, self.labels_data['name'])
        self.assertRedirects(response, reverse('labels:labels-list'))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]), _('Label created successfully'))

    def test_can_not_create_label_with_empty_name(self):
        self.labels_data = {'name': ' '}
        response = self.c.post(reverse('labels:labels-create'),
                               self.labels_data, follow=True)
        self.assertFalse(Label.objects.filter(name=" ").exists())
        message = _('This field is required.')
        self.assertContains(response, message)

    # update

    def test_update_label_response_200(self):
        label = Label.objects.get(name="bug")
        response = self.c.post(
            reverse('labels:labels-update', args=[label.id]),
            self.labels_data, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_update_label_content(self):
        label = Label.objects.get(name="bug")
        response = self.c.get(
            reverse('labels:labels-update', args=[label.id]),
            self.labels_data, follow=True)
        self.assertContains(response, _('Name'))
        self.assertContains(response, _('Edit'))
        self.assertContains(response, 'bug')
        self.assertRegex(
            response.content.decode('utf-8'),
            _(r'\bEdit label\b'))

    def test_update_label_successfully(self):
        label = Label.objects.get(name="bug")
        response = self.c.post(
            reverse('labels:labels-update', args=[label.id]),
            self.labels_data, follow=True)
        label.refresh_from_db()
        self.assertEqual(label.name, self.labels_data['name'])
        self.assertRedirects(response, reverse('labels:labels-list'))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]), _('Label updated successfully'))

    def test_can_not_set_empty_name_when_update_label(self):
        label = Label.objects.get(name="bug")
        self.labels_data = {'name': ' '}
        response = self.c.post(
            reverse('labels:labels-update', args=[label.id]),
            self.labels_data, follow=True)
        self.assertFalse(Label.objects.filter(name=" ").exists())
        message = _('This field is required.')
        self.assertContains(response, message)

    # delete

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
        self.assertContains(response,
                            _('Are you sure you want to delete bug?'))

    def test_delete_label_successfully(self):
        label = Label.objects.get(name="feature")
        response = self.c.post(reverse('labels:labels-delete',
                               args=[label.id]), follow=True)
        self.assertFalse(Label.objects.filter(name="feature").exists())
        self.assertRedirects(response, reverse('labels:labels-list'))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]),
                         _('Label deleted successfully'))

    def test_can_not_delete_label_bound_with_task(self):
        label = Label.objects.get(name="bug")
        response = self.c.post(reverse('labels:labels-delete',
                               args=[label.id]), follow=True)
        self.assertTrue(Label.objects.filter(name="bug").exists())
        self.assertRedirects(response, reverse('labels:labels-list'))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]),
                         _('Cannot delete label because it is in use'))
