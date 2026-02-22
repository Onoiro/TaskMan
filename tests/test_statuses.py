from task_manager.statuses.models import Status
from task_manager.user.models import User
from task_manager.teams.models import Team
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.messages import get_messages
from django.utils.translation import gettext as _
import uuid


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
            'description': 'Test description',
            'color': '#6B7280'
        }
        self.team = Team.objects.get(pk=1)  # user 'me' is member of this team

        # Update UUIDs for fixtures that were loaded without them
        self._update_fixture_uuids()

    def _update_fixture_uuids(self):
        """Update UUIDs for fixture-loaded objects"""
        # Update teams
        team1 = Team.objects.filter(pk=1).first()
        team2 = Team.objects.filter(pk=2).first()
        if team1 and not hasattr(team1, '_uuid_set'):
            team1.uuid = uuid.UUID('550e8400-e29b-41d4-a716-446655440030')
            team1.save(update_fields=['uuid'])
            team1._uuid_set = True
        if team2 and not hasattr(team2, '_uuid_set'):
            team2.uuid = uuid.UUID('550e8400-e29b-41d4-a716-446655440031')
            team2.save(update_fields=['uuid'])
            team2._uuid_set = True

        # Update statuses
        statuses_data = [
            (12, '550e8400-e29b-41d4-a716-446655440010'),
            (13, '550e8400-e29b-41d4-a716-446655440011'),
            (14, '550e8400-e29b-41d4-a716-446655440012'),
            (15, '550e8400-e29b-41d4-a716-446655440013'),
        ]
        for status_pk, status_uuid in statuses_data:
            status = Status.objects.filter(pk=status_pk).first()
            if status:
                status.uuid = uuid.UUID(status_uuid)
                status.save(update_fields=['uuid'])

    def _set_active_team(self, team_id=None):
        """Helper for setting active team in session"""
        session = self.c.session
        if team_id:
            team = Team.objects.get(pk=team_id)
            session['active_team_uuid'] = str(team.uuid)
        else:
            session.pop('active_team_uuid', None)
        session.save()

    # list

    def test_statuses_list_response_200(self):
        response = self.c.get(reverse('statuses:statuses-list'))
        self.assertEqual(response.status_code, 200)

    def test_statuses_list_static_content(self):
        self._set_active_team(self.team.id)

        response = self.c.get(reverse('statuses:statuses-list'))
        self.assertContains(response, _('Statuses'))
        self.assertContains(response, _('New status'))
        self.assertContains(response, _('Tasks'))
        self.assertContains(response, _('Labels'))

    def test_statuses_list_has_tasks_button(self):
        response = self.c.get(reverse('statuses:statuses-list'))
        self.assertContains(response, _("Tasks"))
        self.assertContains(response, reverse('tasks:tasks-list'))

    def test_statuses_list_has_labels_button(self):
        response = self.c.get(reverse('statuses:statuses-list'))
        self.assertContains(response, _("Labels"))
        self.assertContains(response, reverse('labels:labels-list'))

    def test_statuses_list_has_users_button(self):
        response = self.c.get(reverse('statuses:statuses-list'))
        self.assertContains(response, _("Users"))
        self.assertContains(response, reverse('user:user-list'))

    def test_statuses_list_content(self):
        self._set_active_team(self.team.id)

        response = self.c.get(reverse('statuses:statuses-list'))

        team_statuses = Status.objects.filter(team=self.team)

        for status in team_statuses:
            self.assertContains(response, status.name)
            # Check that status is displayed in card format
            self.assertContains(response, 'status-card')

        # other teams statuses and individual statuses should not be displayed
        other_statuses = Status.objects.exclude(team=self.team)
        for status in other_statuses:
            # check that other team statuses are not displayed
            self.assertNotContains(response, status.name)

    def test_statuses_list_content_individual_mode(self):
        # remove active team
        self._set_active_team(None)

        response = self.c.get(reverse('statuses:statuses-list'))

        # show only personal statuses
        personal_statuses = Status.objects.filter(
            creator=self.user,
            team__isnull=True
        )

        for status in personal_statuses:
            self.assertContains(response, status.name)

        # team statuses and other statuses should not be displayed
        team_statuses = Status.objects.filter(team__isnull=False)
        for status in team_statuses:
            self.assertNotContains(response, '#{}'.format(status.id))

    def test_statuses_list_empty_description(self):
        self._set_active_team(self.team.id)

        response = self.c.get(reverse('statuses:statuses-list'))

        # check that there is not "None" displayed if description is empty
        self.assertNotContains(response, ">None<")

        # check that status with description displayed correctly
        status_with_desc = Status.objects.filter(
            team=self.team,
            description__isnull=False,
            description__gt=''
        ).first()

        if status_with_desc:
            self.assertContains(response, status_with_desc.description)

    def test_statuses_list_empty_state(self):
        """Test that empty state is displayed when no statuses."""
        self._set_active_team(self.team.id)

        # Create a test user without any statuses
        test_user = User.objects.create_user(
            username='test_empty_user',
            password='testpass123'
        )
        self.c.force_login(test_user)

        # Set no active team for this user
        self._set_active_team(None)

        response = self.c.get(reverse('statuses:statuses-list'))

        # Check that empty state message is displayed
        self.assertContains(response, _('No statuses found'))
        self.assertContains(
            response, _('Create your first status to organize tasks'))
        self.assertContains(response, _('Create Status'))

    def test_statuses_list_cards_structure(self):
        """Test that statuses are displayed in card format."""
        self._set_active_team(self.team.id)

        response = self.c.get(reverse('statuses:statuses-list'))

        # Check that card structure is present
        self.assertContains(response, 'card border-0 shadow-sm status-card')
        self.assertContains(response, 'card-body p-3')

        # Check that status card has color indicator
        self.assertContains(response, '--status-color:')

        # Check that edit and delete links are present for desktop
        # Hidden on mobile, visible on desktop
        self.assertContains(response, 'd-none d-md-flex')
        self.assertContains(response, '✏️')
        self.assertContains(response, '🗑️')

    def test_statuses_list_task_counter(self):
        """Test that task counter is displayed correctly."""
        self._set_active_team(self.team.id)

        response = self.c.get(reverse('statuses:statuses-list'))

        # Check that task counter is present
        self.assertContains(response, 'task-counter')

        # Check that counter shows correct number of statuses
        status_count = Status.objects.filter(team=self.team).count()
        if status_count > 0:
            self.assertContains(response, str(status_count))

    def test_statuses_list_status_names_have_colors(self):
        """Test that status names in list are displayed with their colors."""
        self._set_active_team(self.team.id)

        status = Status.objects.get(name="new")
        response = self.c.get(reverse('statuses:statuses-list'))

        # Check that the status is displayed with its color
        self.assertContains(response, 'status-card')
        # Check that color CSS variable is set
        self.assertContains(response, '--status-color: {}'.format(status.color))
        # Check that status badge has color styling
        self.assertContains(response, 'status-color-badge')

    def test_create_status_with_description(self):
        self._set_active_team(self.team.id)

        self.c.post(
            reverse('statuses:statuses-create'),
            self.statuses_data,
            follow=True
        )
        status = Status.objects.filter(
            name=self.statuses_data['name']).first()
        self.assertEqual(
            status.description, self.statuses_data['description'])
        self.assertEqual(status.team, self.team)

    def test_update_status_description(self):
        self._set_active_team(self.team.id)

        status = Status.objects.get(name="new")
        new_data = {
            'name': 'updated',
            'description': 'Updated description',
            'color': '#3B82F6'
        }
        self.c.post(reverse('statuses:statuses-update', args=[status.uuid]),
                    new_data, follow=True)
        status.refresh_from_db()
        self.assertEqual(
            status.description, new_data['description'])

    def test_create_status_without_description(self):
        self._set_active_team(self.team.id)

        data_without_desc = {'name': 'no_desc_status', 'color': '#6B7280'}
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
        self._set_active_team(self.team.id)

        response = self.c.post(reverse('statuses:statuses-create'),
                               self.statuses_data, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_created_status_add_to_db(self):
        self._set_active_team(self.team.id)

        old_count = Status.objects.count()
        self.c.post(reverse('statuses:statuses-create'),
                    self.statuses_data, follow=True)
        new_count = Status.objects.count()
        self.assertEqual(old_count + 1, new_count)

    def test_create_status_with_correct_data(self):
        self._set_active_team(self.team.id)

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
        self._set_active_team(self.team.id)

        self.statuses_data = {'name': ' ', 'color': '#6B7280'}
        response = self.c.post(reverse('statuses:statuses-create'),
                               self.statuses_data, follow=True)
        self.assertFalse(Status.objects.filter(name=" ").exists())
        message = _('This field is required.')
        self.assertContains(response, message)

    # update

    def test_get_update_status_response_200_and_check_content(self):
        self._set_active_team(self.team.id)

        status = Status.objects.get(name="new")
        response = self.c.get(reverse('statuses:statuses-update',
                              args=[status.uuid]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, _('Name'))
        self.assertContains(response, _('Edit'))
        self.assertContains(response, 'new')
        self.assertRegex(
            response.content.decode('utf-8'),
            _(r'\bStatus\b')
        )

    def test_update_status_successfully(self):
        self._set_active_team(self.team.id)

        status = Status.objects.get(name="new")
        response = self.c.post(
            reverse('statuses:statuses-update', args=[status.uuid]),
            self.statuses_data, follow=True)
        status.refresh_from_db()
        self.assertEqual(status.name, self.statuses_data['name'])
        self.assertRedirects(response, reverse('statuses:statuses-list'))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]), _('Status updated successfully'))

    def test_can_not_set_empty_name_when_update_status(self):
        self._set_active_team(self.team.id)

        status = Status.objects.get(name="new")
        self.statuses_data = {'name': ' ', 'color': '#6B7280'}
        response = self.c.post(
            reverse('statuses:statuses-update', args=[status.uuid]),
            self.statuses_data, follow=True)
        self.assertFalse(Status.objects.filter(name=" ").exists())
        message = _('This field is required.')
        self.assertContains(response, message)

    def test_update_status_shows_id(self):
        """Test that update status page shows status ID."""
        self._set_active_team(self.team.id)

        status = Status.objects.get(name="new")
        response = self.c.get(
            reverse('statuses:statuses-update', args=[status.uuid]),
            follow=True)

        self.assertContains(response, _('ID'))
        self.assertContains(response, str(status.id))

    def test_update_status_shows_created_at(self):
        """Test that update status page shows creation date."""
        self._set_active_team(self.team.id)

        status = Status.objects.get(name="new")
        response = self.c.get(
            reverse('statuses:statuses-update', args=[status.uuid]),
            follow=True)

        self.assertContains(response, _('Created at'))

    def test_update_status_shows_color(self):
        """Test that update status page shows status color."""
        self._set_active_team(self.team.id)

        status = Status.objects.get(name="new")
        response = self.c.get(
            reverse('statuses:statuses-update', args=[status.uuid]),
            follow=True)

        self.assertContains(response, _('Color'))
        self.assertContains(response, status.color)

    def test_update_status_has_cancel_button(self):
        """Test that update status page has a Cancel button."""
        self._set_active_team(self.team.id)

        status = Status.objects.get(name="new")
        response = self.c.get(
            reverse('statuses:statuses-update', args=[status.uuid]),
            follow=True)

        self.assertContains(response, _('Cancel'))
        # Check that Cancel button links to statuses list
        list_url = reverse('statuses:statuses-list')
        self.assertIn(list_url, response.content.decode('utf-8'))

    def test_update_status_has_delete_button(self):
        """Test that update status page has a Delete button."""
        self._set_active_team(self.team.id)

        status = Status.objects.get(name="new")
        response = self.c.get(
            reverse('statuses:statuses-update', args=[status.uuid]),
            follow=True)

        self.assertContains(response, _('Delete'))
        # Check that Delete button links to delete page
        delete_url = reverse('statuses:statuses-delete', args=[status.uuid])
        self.assertIn(delete_url, response.content.decode('utf-8'))

    # delete

    def test_get_delete_status_response_200_and_check_content(self):
        self._set_active_team(self.team.id)

        status = Status.objects.get(name="new")
        response = self.c.get(
            reverse('statuses:statuses-delete',
                    args=[status.uuid]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, _('Delete status'))
        self.assertContains(response, _('Yes, delete'))
        self.assertContains(response,
                            _('Are you sure you want to delete new?'))

    def test_delete_status_has_cancel_button(self):
        """Test that delete status page has a Cancel button."""
        self._set_active_team(self.team.id)

        status = Status.objects.get(name="new")
        response = self.c.get(
            reverse('statuses:statuses-delete',
                    args=[status.uuid]), follow=True)

        # Check that Cancel button exists
        self.assertContains(response, _('Cancel'))

    def test_delete_status_cancel_button_redirects_to_referer(self):
        """Test that Cancel button redirects to HTTP_REFERER."""
        self._set_active_team(self.team.id)

        status = Status.objects.get(name="new")

        # Set HTTP_REFERER in request
        response = self.c.get(
            reverse('statuses:statuses-delete', args=[status.uuid]),
            HTTP_REFERER=reverse('statuses:statuses-list'),
            follow=True
        )

        # Check that Cancel button is present
        self.assertContains(response, _('Cancel'))

        # The Cancel button href should contain the referer URL
        cancel_url = reverse('statuses:statuses-list')
        self.assertIn(cancel_url, response.content.decode('utf-8'))

    def test_delete_status_cancel_button_without_referer(self):
        """Test that Cancel button redirects to home when no referer."""
        self._set_active_team(self.team.id)

        status = Status.objects.get(name="new")

        # Request without HTTP_REFERER
        response = self.c.get(
            reverse('statuses:statuses-delete', args=[status.uuid]),
            follow=True
        )

        # Check that Cancel button exists and points to home
        self.assertContains(response, _('Cancel'))
        # Button href should be '/' when no referer
        self.assertIn('href="/"', response.content.decode('utf-8'))

    def test_delete_status_successfully(self):
        # to delete status "testing" remove active team
        # because it created by user without team
        self._set_active_team(None)

        test_status = Status.objects.create(
            name="test_to_delete",
            creator=self.user,
            team=None,
            description="Test status for deletion",
            color="#6B7280"
        )

        response = self.c.post(
            reverse('statuses:statuses-delete',
                    args=[test_status.uuid]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Status.objects.filter(name="test_to_delete").exists())
        self.assertRedirects(response, reverse('statuses:statuses-list'))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]),
                         _('Status deleted successfully'))

    def test_can_not_delete_status_bound_with_task(self):
        self._set_active_team(self.team.id)

        status = Status.objects.get(name="new")
        response = self.c.post(
            reverse('statuses:statuses-delete',
                    args=[status.uuid]), follow=True)
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
