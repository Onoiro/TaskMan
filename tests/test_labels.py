from task_manager.labels.models import Label
from task_manager.user.models import User
from task_manager.teams.models import Team
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.messages import get_messages
from django.utils.translation import gettext as _
from django.utils import timezone
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
        self.team = Team.objects.get(pk=1)  # user 'me' is member of this team

    def _set_active_team(self, team_id=None):
        """Helper for setting active team in session"""
        session = self.c.session
        if team_id:
            session['active_team_id'] = team_id
        else:
            session.pop('active_team_id', None)
        session.save()

    # list

    def test_labels_list_response_200(self):
        response = self.c.get(reverse('labels:labels-list'))
        self.assertEqual(response.status_code, 200)

    def test_labels_list_static_content(self):
        self._set_active_team(self.team.id)

        response = self.c.get(reverse('labels:labels-list'))
        self.assertContains(response, 'ID')
        self.assertContains(response, _('Name'))
        self.assertContains(response, _('Created at'))
        self.assertContains(response, _('Labels'))
        self.assertContains(response, _('New label'))

        labels = Label.objects.filter(team=self.team)
        if labels.exists():
            # Edit and Delete buttons show only if there are labels
            self.assertContains(response,
                                reverse('labels:labels-update',
                                        args=[labels.first().id]))
            self.assertContains(response,
                                reverse('labels:labels-delete',
                                        args=[labels.first().id]))

    def test_labels_list_has_tasks_button(self):
        response = self.c.get(reverse('labels:labels-list'))
        self.assertContains(response, _("Tasks"))
        self.assertContains(response, reverse('tasks:tasks-list'))

    def test_labels_list_has_statuses_button(self):
        response = self.c.get(reverse('labels:labels-list'))
        self.assertContains(response, _("Statuses"))
        self.assertContains(response, reverse('statuses:statuses-list'))

    def test_labels_list_content_in_team_mode(self):
        self._set_active_team(self.team.id)

        response = self.c.get(reverse('labels:labels-list'))

        team_labels = Label.objects.filter(team=self.team)

        for label in team_labels:
            self.assertContains(response, label.name)
            local_created_at = timezone.localtime(label.created_at)
            formatted_date = DateFormat(
                local_created_at).format(get_format('DATETIME_FORMAT'))
            self.assertContains(response, formatted_date)

        # labels of other teams and individual labels have not to be shown
        other_labels = Label.objects.exclude(team=self.team)
        for label in other_labels:
            # check labels by id because names can be the same
            self.assertNotContains(response, f'<td>{label.id}</td>')

    def test_labels_list_content_individual_mode(self):
        self._set_active_team(None)

        response = self.c.get(reverse('labels:labels-list'))

        personal_labels = Label.objects.filter(
            creator=self.user,
            team__isnull=True
        )

        for label in personal_labels:
            self.assertContains(response, label.name)
            if label.created_at:
                formatted_date = DateFormat(
                    label.created_at).format(get_format('DATETIME_FORMAT'))
                self.assertContains(response, formatted_date)

        # team labels have not to be shown
        team_labels = Label.objects.filter(team__isnull=False)
        for label in team_labels:
            self.assertNotContains(response, f'<td>{label.id}</td>')

    def test_labels_list_team_switching(self):
        """test team switching"""
        # check team 1
        self._set_active_team(1)
        response = self.c.get(reverse('labels:labels-list'))
        team1_labels = Label.objects.filter(team_id=1)
        for label in team1_labels:
            self.assertContains(response, label.name)

        # switch to team 2
        self._set_active_team(2)
        response = self.c.get(reverse('labels:labels-list'))
        team2_labels = Label.objects.filter(team_id=2)
        for label in team2_labels:
            self.assertContains(response, label.name)
        # team 1 labels not shown if team 2 have no labels
        for label in team1_labels:
            self.assertNotContains(response, f'<td>{label.id}</td>')

    def _get_user_team_labels(self):
        """Helper method to get labels visible to user based on active team"""
        # check active team is set in session
        session = self.c.session
        active_team_id = session.get('active_team_id')

        if active_team_id:
            return Label.objects.filter(team_id=active_team_id)
        else:
            # return labels of user with no team
            return Label.objects.filter(
                creator=self.user,
                team__isnull=True
            )

    def test_labels_list_label_name_is_clickable_link(self):
        """Test that label name in list is a clickable link to edit page."""
        self._set_active_team(self.team.id)

        label = Label.objects.get(name="bug")
        response = self.c.get(reverse('labels:labels-list'))

        # Check that label name is wrapped in <a> tag pointing to edit page
        expected_url = reverse('labels:labels-update', args=[label.id])
        self.assertContains(
            response, f'<a href="{expected_url}">{label.name}</a>', html=True)

    def test_labels_list_edit_delete_buttons_hide_on_mobile(self):
        """Test that Edit and Delete buttons have mobile-hide classes."""
        self._set_active_team(self.team.id)

        response = self.c.get(reverse('labels:labels-list'))

        # Check that buttons have d-none d-md-inline-block classes
        self.assertContains(response, 'd-none d-md-inline-block')

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
        self._set_active_team(self.team.id)

        response = self.c.post(reverse('labels:labels-create'),
                               self.labels_data, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_create_label_successfully(self):
        self._set_active_team(self.team.id)

        old_count = Label.objects.count()
        response = self.c.post(
            reverse('labels:labels-create'),
            self.labels_data, follow=True)
        new_count = Label.objects.count()
        self.assertEqual(old_count + 1, new_count)
        label = Label.objects.filter(
            name=self.labels_data['name']).first()
        self.assertEqual(label.name, self.labels_data['name'])
        # check that label created for team
        self.assertEqual(label.team, self.team)
        self.assertEqual(label.creator, self.user)
        self.assertRedirects(response, reverse('labels:labels-list'))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]), _('Label created successfully'))

    def test_create_label_in_individual_mode(self):
        """Test create label in individuТal mode"""
        # remove active team
        self._set_active_team(None)

        self.c.post(reverse('labels:labels-create'),
                    {'name': 'personal_label'}, follow=True)

        label = Label.objects.filter(name='personal_label').first()
        self.assertIsNotNone(label)
        self.assertIsNone(label.team)
        self.assertEqual(label.creator, self.user)

    def test_can_not_create_label_with_empty_name(self):
        self._set_active_team(self.team.id)

        self.labels_data = {'name': ' '}
        response = self.c.post(reverse('labels:labels-create'),
                               self.labels_data, follow=True)
        self.assertFalse(Label.objects.filter(name=" ").exists())
        message = _('This field is required.')
        self.assertContains(response, message)

    # update

    def test_update_label_response_200(self):
        self._set_active_team(self.team.id)

        label = Label.objects.get(name="bug")
        response = self.c.post(
            reverse('labels:labels-update', args=[label.id]),
            self.labels_data, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_update_label_content(self):
        self._set_active_team(self.team.id)

        label = Label.objects.get(name="bug")
        response = self.c.get(
            reverse('labels:labels-update', args=[label.id]),
            self.labels_data, follow=True)
        self.assertContains(response, _('Name'))
        self.assertContains(response, _('Edit'))
        self.assertContains(response, 'bug')
        self.assertRegex(
            response.content.decode('utf-8'),
            _(r'\bLabel\b'))

    def test_update_label_successfully(self):
        self._set_active_team(self.team.id)

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
        self._set_active_team(self.team.id)

        label = Label.objects.get(name="bug")
        self.labels_data = {'name': ' '}
        response = self.c.post(
            reverse('labels:labels-update', args=[label.id]),
            self.labels_data, follow=True)
        self.assertFalse(Label.objects.filter(name=" ").exists())
        message = _('This field is required.')
        self.assertContains(response, message)

    def test_update_label_in_different_team_mode(self):
        """Test that can't update label from another team"""
        # set active team with id 2
        self._set_active_team(2)

        # try update label from team with id 1
        label = Label.objects.get(name="bug")  # this label is from team 1
        self.c.post(reverse('labels:labels-update',
                            args=[label.id]), {'name': 'hacked'}, follow=True)

        # label doesn't changed
        label.refresh_from_db()
        self.assertEqual(label.name, "bug")

    def test_update_page_has_delete_button(self):
        """Test that update page has a Delete button."""
        self._set_active_team(self.team.id)

        label = Label.objects.get(name="bug")
        response = self.c.get(reverse('labels:labels-update', args=[label.id]))

        self.assertContains(response, _('Delete'))
        delete_url = reverse('labels:labels-delete', args=[label.id])
        self.assertContains(response, f'href="{delete_url}"')

    def test_update_page_has_cancel_button(self):
        """Test that update page has a Cancel button."""
        self._set_active_team(self.team.id)

        label = Label.objects.get(name="bug")
        response = self.c.get(reverse('labels:labels-update', args=[label.id]))

        self.assertContains(response, _('Cancel'))

    def test_update_page_has_label_details_card(self):
        """Test that update page shows label details with ID and Created at."""
        self._set_active_team(self.team.id)

        label = Label.objects.get(name="bug")
        response = self.c.get(reverse('labels:labels-update', args=[label.id]))

        # Check that card exists and contains label details
        self.assertContains(response, 'card')
        self.assertContains(response, label.name)
        self.assertContains(response, label.id)
        # Check that created_at is displayed (formatted date in response)
        self.assertContains(response, 'Created at')

    # delete

    def test_delete_label_response_200(self):
        self._set_active_team(self.team.id)

        # create label without task for delete
        label_to_delete = Label.objects.create(
            name="to_delete",
            creator=self.user,
            team=self.team
        )

        response = self.c.post(reverse('labels:labels-delete',
                               args=[label_to_delete.id]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Label.objects.filter(name="to_delete").exists())

    def test_delete_label_content(self):
        self._set_active_team(self.team.id)

        label = Label.objects.get(name="bug")
        response = self.c.get(reverse('labels:labels-delete',
                              args=[label.id]), follow=True)
        self.assertContains(response, _('Delete label'))
        self.assertContains(response, _('Yes, delete'))
        self.assertContains(response,
                            _('Are you sure you want to delete bug?'))

    def test_delete_label_has_cancel_button(self):
        """Test that delete label page has a Cancel button."""
        self._set_active_team(self.team.id)

        label = Label.objects.get(name="bug")
        response = self.c.get(reverse('labels:labels-delete',
                              args=[label.id]), follow=True)

        # Check that Cancel button exists
        self.assertContains(response, _('Cancel'))

    def test_delete_label_cancel_button_redirects_to_referer(self):
        """Test that Cancel button redirects to HTTP_REFERER."""
        self._set_active_team(self.team.id)

        label = Label.objects.get(name="bug")

        # Set HTTP_REFERER in request
        response = self.c.get(
            reverse('labels:labels-delete', args=[label.id]),
            HTTP_REFERER=reverse('labels:labels-list'),
            follow=True
        )

        # Check that Cancel button is present
        self.assertContains(response, _('Cancel'))

        # The Cancel button href should contain the referer URL
        cancel_url = reverse('labels:labels-list')
        self.assertIn(cancel_url, response.content.decode('utf-8'))

    def test_delete_label_cancel_button_without_referer(self):
        """Test that Cancel button redirects to home when no referer."""
        self._set_active_team(self.team.id)

        label = Label.objects.get(name="bug")

        # Request without HTTP_REFERER
        response = self.c.get(
            reverse('labels:labels-delete', args=[label.id]),
            follow=True
        )

        # Check that Cancel button exists and points to home
        self.assertContains(response, _('Cancel'))
        # Button href should be '/' when no referer
        self.assertIn('href="/"', response.content.decode('utf-8'))

    def test_delete_label_successfully(self):
        self._set_active_team(self.team.id)

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
        self._set_active_team(self.team.id)

        label = Label.objects.get(name="bug")
        response = self.c.post(reverse('labels:labels-delete',
                               args=[label.id]), follow=True)
        self.assertTrue(Label.objects.filter(name="bug").exists())
        self.assertRedirects(response, reverse('labels:labels-list'))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]),
                         _('Cannot delete label because it is in use'))

    def test_delete_label_in_individual_mode(self):
        """Test for delete individual label in individual mode"""
        self._set_active_team(None)

        personal_label = Label.objects.create(
            name="personal_to_delete",
            creator=self.user,
            team=None
        )

        response = self.c.post(
            reverse('labels:labels-delete', args=[personal_label.id]),
            follow=True)

        self.assertFalse(
            Label.objects.filter(name="personal_to_delete").exists()
        )
        self.assertRedirects(response, reverse('labels:labels-list'))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]), _('Label deleted successfully'))
