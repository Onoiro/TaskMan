from task_manager.user.models import User
from task_manager.teams.models import Team, TeamMembership
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.messages import get_messages
from django.utils.translation import gettext as _


class TeamTestCase(TestCase):
    fixtures = ["tests/fixtures/test_users.json",
                "tests/fixtures/test_teams.json",
                "tests/fixtures/test_teams_memberships.json",
                "tests/fixtures/test_statuses.json",
                "tests/fixtures/test_tasks.json",
                "tests/fixtures/test_labels.json"]

    def setUp(self):
        self.admin_user = User.objects.get(pk=10)  # User who will be team admin
        self.c = Client()
        self.c.force_login(self.admin_user)
        self.team_data = {
            'name': 'New Test Team',
            'description': 'This is a new test team',
            'password1': '111',
            'password2': '111'
        }
        self.team = Team.objects.get(pk=1)  # Test Team

    def _get_user_teams(self, user):
        """Helper to get user's teams"""
        # Используем related_name 'member_teams' из ManyToMany поля
        return user.member_teams.all()

    # create

    def test_team_create_page_response_200_and_content(self):
        response = self.c.get(reverse('teams:team-create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, _('Name'))
        self.assertContains(response, _('Description'))
        self.assertRegex(
            response.content.decode('utf-8'), _(r'\bCreate Team\b'))

    def test_create_team_successfully(self):
        old_count = Team.objects.count()
        response = self.c.post(reverse('teams:team-create'),
                               self.team_data, follow=True)
        self.assertEqual(response.status_code, 200)
        new_count = Team.objects.count()
        self.assertEqual(old_count + 1, new_count)

        team = Team.objects.filter(name=self.team_data['name']).first()
        self.assertEqual(team.description, self.team_data['description'])
        
        # Check that the user is admin of the team using built-in method
        self.assertTrue(team.is_admin(self.admin_user))

        # check that the user is a member of the team
        self.assertTrue(team.is_member(self.admin_user))
        
        # Alternative: check through user's teams
        user_teams = self._get_user_teams(self.admin_user)
        self.assertIn(team, user_teams)

        # check redirect and message
        self.assertRedirects(response, reverse('index'))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]), _('Team created successfully'))

    def test_check_for_not_create_team_with_same_name(self):
        # create a team
        self.c.post(reverse('teams:team-create'), self.team_data, follow=True)
        teams_count = Team.objects.count()

        # try to create team with the same name
        response = self.c.post(
            reverse('teams:team-create'),
            self.team_data, follow=True)
        new_teams_count = Team.objects.count()

        # check that new team has no created
        self.assertEqual(teams_count, new_teams_count)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, _('Team with this Name already exists.'))

    def test_can_not_create_team_with_empty_name(self):
        empty_name_data = self.team_data.copy()
        empty_name_data['name'] = ''
        response = self.c.post(reverse('teams:team-create'),
                               empty_name_data, follow=True)
        self.assertFalse(Team.objects.filter(name="").exists())
        self.assertContains(response, _('This field is required.'))

    # update

    def test_update_team_status_200_and_check_content(self):
        # Make sure user is admin of the team
        if not self.team.is_admin(self.admin_user):
            TeamMembership.objects.update_or_create(
                user=self.admin_user,
                team=self.team,
                defaults={'role': 'admin'}
            )
        
        response = self.c.get(
            reverse('teams:team-update', args=[self.team.id]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, _('Name'))
        self.assertContains(response, _('Description'))
        self.assertRegex(
            response.content.decode('utf-8'), _(r'\bEdit Team\b'))
        self.assertContains(response, self.team.name)
        self.assertContains(response, self.team.description)

    def test_update_team_successfully(self):
        # Make sure user is admin of the team
        if not self.team.is_admin(self.admin_user):
            TeamMembership.objects.update_or_create(
                user=self.admin_user,
                team=self.team,
                defaults={'role': 'admin'}
            )
        
        updated_team_data = {
            'name': 'Updated Team Name',
            'description': 'Updated description',
            'password1': '111',
            'password2': '111'
        }
        response = self.c.post(
            reverse('teams:team-update', args=[self.team.id]),
            updated_team_data, follow=True)
        self.assertEqual(response.status_code, 200)

        self.team.refresh_from_db()
        self.assertEqual(self.team.name, updated_team_data['name'])
        self.assertEqual(self.team.description,
                         updated_team_data['description'])

        # check redirect and message
        self.assertRedirects(response, reverse('user:user-list'))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]), _('Team updated successfully'))

    def test_update_team_with_existing_name(self):
        # Make sure user is admin of the team
        if not self.team.is_admin(self.admin_user):
            TeamMembership.objects.update_or_create(
                user=self.admin_user,
                team=self.team,
                defaults={'role': 'admin'}
            )
        
        second_team = Team.objects.get(pk=2)  # Another Test Team из фикстур

        # try to update first team with name of second team
        update_data = {
            'name': second_team.name,
            'description': 'Updated description',
            'password1': '111',
            'password2': '111'
        }
        response = self.c.post(
            reverse('teams:team-update', args=[self.team.id]),
            update_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, _('Team with this Name already exists.'))

        # check that name has not changed
        self.team.refresh_from_db()
        self.assertNotEqual(self.team.name, second_team.name)

    def test_non_admin_cannot_update_team(self):
        # create regular user not team admin
        regular_user = User.objects.create_user(
            username='regular_user',
            password='password123'
        )
        # add regular user to team as member (not admin)
        TeamMembership.objects.create(
            user=regular_user,
            team=self.team,
            role='member'
        )

        # login as regular user
        self.c.logout()
        self.c.force_login(regular_user)

        # try to get team update form
        response = self.c.get(
            reverse('teams:team-update', args=[self.team.id]), follow=True)

        # check for redirect
        self.assertEqual(len(response.redirect_chain), 1)

        # check for error message
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(
            str(messages[0]),
            _("You don't have permissions to modify this."
              " Only team admin can do this.")
        )

        # now try to direct POST request
        updated_data = {
            'name': 'Updated by non-admin',
            'description': 'Should not work',
            'password1': '111',
            'password2': '111'
        }
        response = self.c.post(
            reverse('teams:team-update', args=[self.team.id]),
            updated_data, follow=True)

        # check that data has not been changed
        self.team.refresh_from_db()
        self.assertNotEqual(self.team.name, updated_data['name'])

    # delete

    def test_get_delete_team_response_200_and_check_content(self):
        # Make sure user is admin of the team
        if not self.team.is_admin(self.admin_user):
            TeamMembership.objects.update_or_create(
                user=self.admin_user,
                team=self.team,
                defaults={'role': 'admin'}
            )
        
        response = self.c.get(
            reverse('teams:team-delete', args=[self.team.id]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, _('Delete team'))
        self.assertContains(response, _('Yes, delete'))
        self.assertContains(response,
                            _('Are you sure you want to delete'))

    def test_delete_team_successfully(self):
        # create new team for deleting
        response = self.c.post(reverse('teams:team-create'),
                    self.team_data, follow=True)
        team = Team.objects.get(name=self.team_data['name'])
        team_id = team.id  # Сохраняем ID для проверки после удаления
        
        # Ensure user is admin of this new team
        # (should be created automatically by the view)
        self.assertTrue(team.is_admin(self.admin_user))

        # check teams count before deleting
        teams_count = Team.objects.count()

        # delete team
        response = self.c.post(reverse('teams:team-delete',
                                       args=[team.id]), follow=True)

        # check team has been deleted
        self.assertEqual(Team.objects.count(), teams_count - 1)
        self.assertFalse(Team.objects.filter(
            name=self.team_data['name']).exists())

        # check redirect and message
        self.assertRedirects(response, reverse('user:user-list'))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]), _('Team deleted successfully'))

        # Check that user has no membership in deleted team
        self.assertFalse(
            TeamMembership.objects.filter(
                user=self.admin_user, 
                team_id=team_id  # Используем сохраненный ID
            ).exists()
        )

    def test_cannot_delete_team_with_members(self):
        # Make sure admin user is admin of the team
        if not self.team.is_admin(self.admin_user):
            TeamMembership.objects.update_or_create(
                user=self.admin_user,
                team=self.team,
                defaults={'role': 'admin'}
            )
        
        # add regular user to team
        regular_user = User.objects.create_user(
            username='team_member',
            password='password123'
        )
        TeamMembership.objects.create(
            user=regular_user,
            team=self.team,
            role='member'
        )

        # try to delete team
        response = self.c.post(reverse('teams:team-delete',
                                       args=[self.team.id]), follow=True)

        # check that team still exists
        self.assertTrue(Team.objects.filter(pk=self.team.id).exists())

        # check redirect and error message
        self.assertRedirects(response, reverse('user:user-list'))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]),
                         _("Cannot delete a team because it has members."))

    def test_non_admin_cannot_delete_team(self):
        # create regular user not team admin
        regular_user = User.objects.create_user(
            username='regular_user_delete',
            password='password123'
        )

        # login as regular user
        self.c.logout()
        self.c.force_login(regular_user)

        # try to delete team
        teams_count = Team.objects.count()
        response = self.c.post(reverse('teams:team-delete',
                            args=[self.team.id]), follow=True)

        # check that team exists
        self.assertEqual(Team.objects.count(), teams_count)
        self.assertTrue(Team.objects.filter(pk=self.team.id).exists())
        
        # Check for error message (if redirected)
        messages = list(get_messages(response.wsgi_request))
        if messages:
            self.assertIn(
                _("You don't have permissions"),
                str(messages[0])
            )
