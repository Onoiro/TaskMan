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
        self.admin_user = User.objects.get(pk=10)  # user team admin
        self.c = Client()
        self.c.force_login(self.admin_user)
        self.team_data = {
            'name': 'New Test Team',
            'description': 'This is a new test team',
            'password1': '111',
            'password2': '111'
        }
        self.team = Team.objects.get(pk=1)  # test team

    def _get_user_teams(self, user):
        """Helper to get user's teams"""
        # using the related_name 'member_teams' for the ManyToMany field
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

        # check that the user is admin of the team using built-in method
        self.assertTrue(team.is_admin(self.admin_user))

        # check that the user is a member of the team
        self.assertTrue(team.is_member(self.admin_user))

        # alternative: check through user's teams
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
        # make sure user is admin of the team
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
        # make sure user is admin of the team
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
        # make sure user is admin of the team
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
        # make sure user is admin of the team
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

    def test_delete_team_has_cancel_button(self):
        """Test that delete team page has a Cancel button."""
        # make sure user is admin of the team
        if not self.team.is_admin(self.admin_user):
            TeamMembership.objects.update_or_create(
                user=self.admin_user,
                team=self.team,
                defaults={'role': 'admin'}
            )

        response = self.c.get(
            reverse('teams:team-delete', args=[self.team.id]), follow=True)

        # Check that Cancel button exists
        self.assertContains(response, _('Cancel'))

    def test_delete_team_cancel_button_redirects_to_referer(self):
        """Test that Cancel button redirects to HTTP_REFERER."""
        # make sure user is admin of the team
        if not self.team.is_admin(self.admin_user):
            TeamMembership.objects.update_or_create(
                user=self.admin_user,
                team=self.team,
                defaults={'role': 'admin'}
            )

        # Set HTTP_REFERER in request
        response = self.c.get(
            reverse('teams:team-delete', args=[self.team.id]),
            HTTP_REFERER=reverse('user:user-list'),
            follow=True
        )

        # Check that Cancel button is present
        self.assertContains(response, _('Cancel'))

        # The Cancel button href should contain the referer URL
        cancel_url = reverse('user:user-list')
        self.assertIn(cancel_url, response.content.decode('utf-8'))

    def test_delete_team_cancel_button_without_referer(self):
        """Test that Cancel button redirects to home when no referer."""
        # make sure user is admin of the team
        if not self.team.is_admin(self.admin_user):
            TeamMembership.objects.update_or_create(
                user=self.admin_user,
                team=self.team,
                defaults={'role': 'admin'}
            )

        # Request without HTTP_REFERER
        response = self.c.get(
            reverse('teams:team-delete', args=[self.team.id]),
            follow=True
        )

        # Check that Cancel button exists and points to home
        self.assertContains(response, _('Cancel'))
        # Button href should be '/' when no referer
        self.assertIn('href="/"', response.content.decode('utf-8'))

    def test_delete_team_successfully(self):
        # create new team for deleting
        response = self.c.post(reverse('teams:team-create'),
                               self.team_data, follow=True)
        team = Team.objects.get(name=self.team_data['name'])
        team_id = team.id  # save id for check after deleting

        # ensure user is admin of this new team
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

        # check that user has no membership in deleted team
        self.assertFalse(
            TeamMembership.objects.filter(
                user=self.admin_user,
                team_id=team_id  # use saved id
            ).exists()
        )

    def test_cannot_delete_team_with_members(self):
        # make sure admin user is admin of the team
        if not self.team.is_admin(self.admin_user):
            TeamMembership.objects.update_or_create(
                user=self.admin_user,
                team=self.team,
                defaults={'role': 'admin'}
            )

        # remove all tasks related to the team
        # to avoid triggering the task check
        from task_manager.tasks.models import Task
        Task.objects.filter(team=self.team).delete()

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
                         _("Cannot delete a team because"
                         " it has other members."))

    def test_cannot_delete_team_with_tasks(self):
        # create a new team without any members (only admin)
        new_team = Team.objects.create(
            name='Task Team',
            description='Team with tasks',
            password='123'
        )
        TeamMembership.objects.create(
            user=self.admin_user,
            team=new_team,
            role='admin'
        )

        # add a task to the team
        from task_manager.tasks.models import Task, Status
        status = Status.objects.first()
        Task.objects.create(
            name='Test Task',
            description='Task description',
            status=status,
            author=self.admin_user,
            executor=self.admin_user,
            team=new_team
        )

        # attempt to delete the team
        response = self.c.post(
            reverse('teams:team-delete', args=[new_team.id]), follow=True)

        # ensure the team still exists
        self.assertTrue(Team.objects.filter(pk=new_team.id).exists())

        # check the error message about tasks
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(str(messages[0]),
                         _("Cannot delete a team because it has tasks."))

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

        # check for error message (if redirected)
        messages = list(get_messages(response.wsgi_request))
        if messages:
            self.assertIn(
                _("You don't have permissions"),
                str(messages[0])
            )

    # exit team

    def test_exit_team_successfully(self):
        # create a regular user who is a member of the team
        regular_user = User.objects.create_user(
            username='regular_member',
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

        # set active team in session
        self.c.session['active_team_id'] = self.team.id
        self.c.session.save()

        # check membership exists before exit
        self.assertTrue(self.team.is_member(regular_user))
        self.assertEqual(regular_user.member_teams.count(), 1)

        # exit the team
        response = self.c.post(reverse('teams:team-exit', args=[self.team.id]),
                               follow=True)

        # check that membership was removed
        self.assertFalse(self.team.is_member(regular_user))
        self.assertEqual(regular_user.member_teams.count(), 0)

        # check that active team was cleared from session
        self.assertNotIn('active_team_id', self.c.session)

        # check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertIn(
            _('You have successfully left the team'),
            str(messages[0]))

    def test_cannot_exit_team_as_admin(self):
        # create a new team where admin_user is the admin
        new_team = Team.objects.create(
            name='Admin Team',
            description='Team for admin exit test',
            password='123'
        )
        TeamMembership.objects.create(
            user=self.admin_user,
            team=new_team,
            role='admin'
        )

        # try to exit as admin
        response = self.c.get(
            reverse('teams:team-exit',
                    args=[new_team.id]), follow=True)

        # check that membership still exists
        self.assertTrue(new_team.is_member(self.admin_user))
        self.assertTrue(new_team.is_admin(self.admin_user))

        # check error message
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertIn(_('Team administrators cannot leave the team'),
                      str(messages[0]))

    def test_cannot_exit_team_with_tasks(self):
        from task_manager.tasks.models import Task
        from task_manager.statuses.models import Status

        # create a regular user who is a member of the team
        regular_user = User.objects.create_user(
            username='task_user',
            password='password123'
        )

        # add regular user to team as member
        TeamMembership.objects.create(
            user=regular_user,
            team=self.team,
            role='member'
        )

        # get a status for the task
        status = Status.objects.first()

        # create a task where user is the author
        Task.objects.create(
            name='Test Task',
            description='Task description',
            status=status,
            author=regular_user,
            executor=self.admin_user,  # different user as executor
            team=self.team
        )

        # login as regular user
        self.c.logout()
        self.c.force_login(regular_user)

        # try to exit the team
        response = self.c.get(
            reverse('teams:team-exit',
                    args=[self.team.id]), follow=True)

        # check that membership still exists
        self.assertTrue(self.team.is_member(regular_user))

        # check error message
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertIn(_('You cannot exit the team because you'
                      ' are author or executor of tasks'),
                      str(messages[0]))

    def test_cannot_exit_team_as_executor(self):
        from task_manager.tasks.models import Task
        from task_manager.statuses.models import Status

        # create a regular user who is a member of the team
        regular_user = User.objects.create_user(
            username='executor_user',
            password='password123'
        )

        # add regular user to team as member
        TeamMembership.objects.create(
            user=regular_user,
            team=self.team,
            role='member'
        )

        # get a status for the task
        status = Status.objects.first()

        # create a task where user is the executor
        Task.objects.create(
            name='Executor Task',
            description='Task for executor test',
            status=status,
            author=self.admin_user,  # different user as author
            executor=regular_user,
            team=self.team
        )

        # login as regular user
        self.c.logout()
        self.c.force_login(regular_user)

        # try to exit the team
        response = self.c.get(
            reverse('teams:team-exit',
                    args=[self.team.id]), follow=True)

        # check that membership still exists
        self.assertTrue(self.team.is_member(regular_user))

        # check error message
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertIn(_('You cannot exit the team because you'
                      ' are author or executor of tasks'),
                      str(messages[0]))

    def test_cannot_exit_nonexistent_team(self):
        """test that user cannot exit a team that doesn't exist"""
        nonexistent_team_id = 9999

        # try to exit nonexistent team
        response = self.c.post(
            reverse('teams:team-exit',
                    args=[nonexistent_team_id]), follow=True)

        # check error message
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]), _('Team not found'))

    def test_cannot_exit_team_not_member(self):
        # create a user who is not a member of any team
        non_member_user = User.objects.create_user(
            username='non_member',
            password='password123'
        )

        # login as non-member user
        self.c.logout()
        self.c.force_login(non_member_user)

        # try to exit the team
        response = self.c.get(reverse('teams:team-exit',
                              args=[self.team.id]),
                              follow=True)

        # check error message
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]),
                         _('You are not a member of this team'))

    # switch team tests

    def test_switch_to_team_successfully(self):
        """test switching to a team where user is a member"""
        # ensure user is a member of the team
        if not self.team.is_member(self.admin_user):
            TeamMembership.objects.create(
                user=self.admin_user,
                team=self.team,
                role='admin'
            )

        # switch to team
        response = self.c.post(
            reverse('teams:switch-team'),
            {'team_id': self.team.id},
            follow=True
        )

        # check that active_team_id is set in session
        self.assertEqual(self.c.session.get('active_team_id'), self.team.id)

        # check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertIn(
            _('Switched to team'),
            str(messages[0])
        )

    def test_switch_to_individual_mode(self):
        """test switching to individual mode from team mode"""
        # set active team in session
        session = self.c.session
        session['active_team_id'] = self.team.id
        session.save()

        # switch to individual mode
        response = self.c.post(
            reverse('teams:switch-team'),
            {'team_id': 'individual'},
            follow=True
        )

        # check that active_team_id is removed from session
        self.assertNotIn('active_team_id', self.c.session)

        # check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(
            str(messages[0]),
            _('Switched to individual mode')
        )

    def test_cannot_switch_to_nonexistent_team(self):
        """test that user cannot switch to a team that doesn't exist"""
        nonexistent_team_id = 9999

        # try to switch to nonexistent team
        response = self.c.post(
            reverse('teams:switch-team'),
            {'team_id': nonexistent_team_id},
            follow=True
        )

        # check that active_team_id is not set
        self.assertNotIn('active_team_id', self.c.session)

        # check error message
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]), _('Team not found'))

    def test_cannot_switch_to_team_not_member(self):
        """test that user cannot switch to a team they are not a member of"""
        # create a user who is not a member of the team
        non_member_user = User.objects.create_user(
            username='non_member_switch',
            password='password123'
        )

        # login as non-member user
        self.c.logout()
        self.c.force_login(non_member_user)

        # try to switch to team
        response = self.c.post(
            reverse('teams:switch-team'),
            {'team_id': self.team.id},
            follow=True
        )

        # check that active_team_id is not set
        self.assertNotIn('active_team_id', self.c.session)

        # check error message
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]), _('Team not found'))

    def test_switch_team_without_team_id(self):
        """test switching without providing team_id"""
        # set active team in session
        session = self.c.session
        session['active_team_id'] = self.team.id
        session.save()

        # call switch without team_id
        self.c.post(reverse('teams:switch-team'), {}, follow=True)

        # check that active_team_id is still in session (unchanged)
        self.assertEqual(self.c.session.get('active_team_id'), self.team.id)

    # team detail tests

    def test_team_detail_page_response_200_and_content(self):
        """test that team detail page displays correctly"""
        response = self.c.get(
            reverse('teams:team-detail', args=[self.team.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.team.name)
        self.assertContains(response, self.team.description)

    def test_team_detail_shows_members(self):
        """test that team detail page shows all team members"""
        # create additional member
        new_member = User.objects.create_user(
            username='detail_member',
            password='password123'
        )
        TeamMembership.objects.create(
            user=new_member,
            team=self.team,
            role='member'
        )

        response = self.c.get(
            reverse('teams:team-detail', args=[self.team.id])
        )

        # check that memberships are in context
        self.assertIn('memberships', response.context)
        memberships = response.context['memberships']

        # check that new member is in the list
        member_users = [m.user for m in memberships]
        self.assertIn(new_member, member_users)

    def test_team_detail_shows_admin_status(self):
        """test that team detail correctly identifies admin status"""
        # ensure admin_user is admin
        if not self.team.is_admin(self.admin_user):
            TeamMembership.objects.update_or_create(
                user=self.admin_user,
                team=self.team,
                defaults={'role': 'admin'}
            )

        response = self.c.get(
            reverse('teams:team-detail', args=[self.team.id])
        )

        # check that is_admin is True in context
        self.assertIn('is_admin', response.context)
        self.assertTrue(response.context['is_admin'])

        # now test with regular member
        regular_member = User.objects.create_user(
            username='regular_detail',
            password='password123'
        )
        TeamMembership.objects.create(
            user=regular_member,
            team=self.team,
            role='member'
        )

        self.c.logout()
        self.c.force_login(regular_member)

        response = self.c.get(
            reverse('teams:team-detail', args=[self.team.id])
        )

        # check that is_admin is False in context
        self.assertIn('is_admin', response.context)
        self.assertFalse(response.context['is_admin'])

    def test_team_detail_context_contains_team(self):
        """test that team detail context contains team object"""
        response = self.c.get(
            reverse('teams:team-detail', args=[self.team.id])
        )

        # check that team is in context with correct context_object_name
        self.assertIn('team', response.context)
        self.assertEqual(response.context['team'], self.team)

    # team member role update tests

    def test_team_member_role_update_page_response_200_and_content(self):
        """test that role update page displays correctly"""
        # create a member to update
        member = User.objects.create_user(
            username='member_to_update',
            password='password123'
        )
        membership = TeamMembership.objects.create(
            user=member,
            team=self.team,
            role='member'
        )

        # ensure admin_user is admin
        if not self.team.is_admin(self.admin_user):
            TeamMembership.objects.update_or_create(
                user=self.admin_user,
                team=self.team,
                defaults={'role': 'admin'}
            )

        response = self.c.get(
            reverse('teams:team-member-role-update', args=[membership.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, member.username)

    def test_promote_member_to_admin(self):
        """test promoting a member to admin role"""
        # create a member
        member = User.objects.create_user(
            username='member_to_promote',
            password='password123'
        )
        membership = TeamMembership.objects.create(
            user=member,
            team=self.team,
            role='member'
        )

        # ensure admin_user is admin
        if not self.team.is_admin(self.admin_user):
            TeamMembership.objects.update_or_create(
                user=self.admin_user,
                team=self.team,
                defaults={'role': 'admin'}
            )

        # promote to admin
        response = self.c.post(
            reverse('teams:team-member-role-update', args=[membership.id]),
            {'role': 'admin'},
            follow=True
        )

        # check that role was updated
        membership.refresh_from_db()
        self.assertEqual(membership.role, 'admin')

        # check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertIn(
            _('has been promoted to team admin'),
            str(messages[0])
        )

    def test_demote_admin_to_member(self):
        """test demoting an admin to member role"""
        # create an admin member
        admin_member = User.objects.create_user(
            username='admin_to_demote',
            password='password123'
        )
        membership = TeamMembership.objects.create(
            user=admin_member,
            team=self.team,
            role='admin'
        )

        # ensure admin_user is admin
        if not self.team.is_admin(self.admin_user):
            TeamMembership.objects.update_or_create(
                user=self.admin_user,
                team=self.team,
                defaults={'role': 'admin'}
            )

        # demote to member
        response = self.c.post(
            reverse('teams:team-member-role-update', args=[membership.id]),
            {'role': 'member'},
            follow=True
        )

        # check that role was updated
        membership.refresh_from_db()
        self.assertEqual(membership.role, 'member')

        # check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertIn(
            _('has been demoted to team member'),
            str(messages[0])
        )

    def test_update_member_role_to_same_role(self):
        """test updating member role to the same role (no change)"""
        # create a member
        member = User.objects.create_user(
            username='member_same_role',
            password='password123'
        )
        membership = TeamMembership.objects.create(
            user=member,
            team=self.team,
            role='member'
        )

        # ensure admin_user is admin
        if not self.team.is_admin(self.admin_user):
            TeamMembership.objects.update_or_create(
                user=self.admin_user,
                team=self.team,
                defaults={'role': 'admin'}
            )

        # update to the same role
        response = self.c.post(
            reverse('teams:team-member-role-update', args=[membership.id]),
            {'role': 'member'},
            follow=True
        )

        # check that role is still member
        membership.refresh_from_db()
        self.assertEqual(membership.role, 'member')

        # check redirect happened
        self.assertRedirects(response, reverse('user:user-list'))

    def test_non_admin_cannot_update_member_role(self):
        """test that non-admin cannot update member roles"""
        # create two members
        member1 = User.objects.create_user(
            username='member1_role',
            password='password123'
        )
        member2 = User.objects.create_user(
            username='member2_role',
            password='password123'
        )

        TeamMembership.objects.create(
            user=member1,
            team=self.team,
            role='member'
        )
        membership2 = TeamMembership.objects.create(
            user=member2,
            team=self.team,
            role='member'
        )

        # login as member1 (not admin)
        self.c.logout()
        self.c.force_login(member1)

        # try to update member2's role
        response = self.c.post(
            reverse('teams:team-member-role-update', args=[membership2.id]),
            {'role': 'admin'},
            follow=True
        )

        # check that role was not updated
        membership2.refresh_from_db()
        self.assertEqual(membership2.role, 'member')

        # check error message
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertIn(
            _("You don't have permissions"),
            str(messages[0])
        )

    def test_non_admin_cannot_access_role_update_page(self):
        """test that non-admin cannot even access the role update page"""
        # create two members
        member1 = User.objects.create_user(
            username='member1_get',
            password='password123'
        )
        member2 = User.objects.create_user(
            username='member2_get',
            password='password123'
        )

        TeamMembership.objects.create(
            user=member1,
            team=self.team,
            role='member'
        )
        membership2 = TeamMembership.objects.create(
            user=member2,
            team=self.team,
            role='member'
        )

        # login as member1 (not admin)
        self.c.logout()
        self.c.force_login(member1)

        # try to access the update page
        response = self.c.get(
            reverse('teams:team-member-role-update', args=[membership2.id]),
            follow=True
        )

        # check for error message
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertIn(
            _("You don't have permissions"),
            str(messages[0])
        )
