from task_manager.user.models import User
from task_manager.teams.models import Team, TeamMembership
from task_manager.statuses.models import Status
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.messages import get_messages
from django.utils.translation import gettext as _
from django.contrib.auth.hashers import check_password


class UserTestCase(TestCase):
    fixtures = ["tests/fixtures/test_teams.json",
                "tests/fixtures/test_users.json",
                "tests/fixtures/test_teams_memberships.json",
                "tests/fixtures/test_statuses.json",
                "tests/fixtures/test_tasks.json",
                "tests/fixtures/test_labels.json"]

    def setUp(self):
        self.user = User.objects.get(username="he")
        self.c = Client()
        self.c.force_login(self.user)
        self.user_data = {
            'first_name': 'New',
            'last_name': 'N',
            'username': 'new',
            'description': 'Test description',
            'password1': '222',
            'password2': '222',
            'join_team_name': '',
            'join_team_password': ''
        }

    # list

    def test_user_list_response_200(self):
        response = self.c.get(reverse('user:user-list'))
        self.assertEqual(response.status_code, 200)

    def test_user_list_content(self):
        response = self.c.get(reverse('user:user-list'))
        self.assertContains(response, _('Users'))
        # Check that user card design is present
        self.assertContains(response, 'user-card')
        # Check that toolbar is present
        self.assertContains(response, 'toolbar-row')
        # Check that user counter is present
        self.assertContains(response, 'task-counter')
        # Check that reference book links are present
        self.assertContains(response, 'Tasks')
        self.assertContains(response, 'Statuses')
        self.assertContains(response, 'Labels')

    def test_user_list_unauthenticated(self):
        """test that unauthenticated users get empty queryset"""
        self.c.logout()
        response = self.c.get(reverse('user:user-list'))
        self.assertEqual(response.status_code, 200)
        # should return empty queryset for unauthenticated users
        self.assertQuerySetEqual(response.context['user_list'], [])

    # to do later - this test fails

    # def test_user_list_with_team_context(self):
    #     """test user list with active team context"""
    #     # set active team in session
    #     self.c.session['active_team_id'] = 1
    #     self.c.session.save()

    #     response = self.c.get(reverse('user:user-list'))
    #     self.assertEqual(response.status_code, 200)

    #     # check that user_memberships context is present
    #     self.assertIn('user_memberships', response.context)
    #     self.assertIn('user_membership', response.context)

    #     # should show team users that current user can see
    #     # user 'he' (id=12) should see himself and possibly other team members
    #     team_users = response.context['user_list']
    #     actual_user_ids = [user.id for user in team_users]

    #     # at minimum, current user should be in the list
    #     self.assertIn(self.user.id, actual_user_ids)

    #     # check that user_memberships contains memberships for team 1
    #     user_memberships = response.context['user_memberships']
    #     membership_user_ids = [m.user.id for m in user_memberships]
    #     expected_membership_user_ids = [10, 12]  # from fixtures
    #     self.assertEqual(sorted(membership_user_ids),
    #  sorted(expected_membership_user_ids))

    def test_user_list_without_team_context(self):
        """test user list without active team"""
        # ensure no active team
        if 'active_team_id' in self.c.session:
            del self.c.session['active_team_id']
        self.c.session.save()

        response = self.c.get(reverse('user:user-list'))
        self.assertEqual(response.status_code, 200)

        # should show only current user
        users = response.context['user_list']
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0].id, self.user.id)

        # check context is empty
        self.assertEqual(response.context['user_memberships'], [])
        self.assertIsNone(response.context['user_membership'])

    # to do later - this test fails

    # def test_user_list_user_membership_context(self):
    #     """test that user membership context is correctly set"""
    #     self.c.session['active_team_id'] = 1
    #     self.c.session.save()

    #     response = self.c.get(reverse('user:user-list'))
    #     self.assertEqual(response.status_code, 200)

    #     # user 'he' (id=12) should have membership in team 1
    #     user_membership = response.context['user_membership']
    #     self.assertIsNotNone(user_membership)
    #     self.assertEqual(user_membership.user.id, self.user.id)
    #     self.assertEqual(user_membership.team.id, 1)
    #     self.assertEqual(user_membership.role, 'member')

    # detail

    def test_user_detail_view_response_200(self):
        """test user detail view returns 200"""
        response = self.c.get(reverse('user:user-detail', args=[self.user.id]))
        self.assertEqual(response.status_code, 200)

    def test_user_detail_view_context(self):
        """test user detail view context data"""
        response = self.c.get(reverse('user:user-detail', args=[self.user.id]))
        self.assertEqual(response.status_code, 200)

        # check context object is correct
        self.assertEqual(response.context['object'].id, self.user.id)

        # check user_teams context is present
        self.assertIn('user_teams', response.context)

        # user 'he' should have one team membership
        user_teams = response.context['user_teams']
        self.assertEqual(len(user_teams), 1)
        self.assertEqual(user_teams[0].team.id, 1)

    def test_user_detail_view_shows_description(self):
        """test user detail view shows description field"""
        # user 'me' has description in fixture
        user_with_desc = User.objects.get(username='me')
        response = self.c.get(reverse('user:user-detail',
                                      args=[user_with_desc.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, _('Description'))
        self.assertContains(response, 'Team administrator and task creator')

    def test_user_detail_view_without_description(self):
        """test user detail view shows empty when no description"""
        user_without_desc = User.objects.get(username='he')
        response = self.c.get(reverse('user:user-detail',
                                      args=[user_without_desc.id]))
        self.assertEqual(response.status_code, 200)
        # Description label should still be present
        self.assertContains(response, _('Description'))
        # But no description text

    def test_user_detail_view_user_without_teams(self):
        """test user detail view for user without teams"""
        alone_user = User.objects.get(username='alone')
        response = self.c.get(reverse(
            'user:user-detail', args=[alone_user.id]))
        self.assertEqual(response.status_code, 200)

        # should have empty user_teams
        user_teams = response.context['user_teams']
        self.assertEqual(len(user_teams), 0)

    def test_user_detail_edit_delete_buttons_for_current_user(self):
        """test that Edit/Delete buttons are shown only for current user"""
        # User should see Edit/Delete buttons on their own detail page
        response = self.c.get(reverse('user:user-detail', args=[self.user.id]))
        self.assertEqual(response.status_code, 200)

        # Check that Edit and Delete buttons are present for current user
        self.assertContains(response, 'Edit')
        self.assertContains(response, 'Delete')

    def test_user_detail_no_edit_delete_buttons_for_other_user(self):
        """test that Edit/Delete buttons are not shown for other users"""
        # Test with another user from fixtures
        other_user = User.objects.get(username='me')
        response = self.c.get(reverse('user:user-detail', args=[other_user.id]))
        self.assertEqual(response.status_code, 200)

        # Check that Edit and Delete buttons are NOT present for other users
        self.assertNotContains(response, 'Edit')
        self.assertNotContains(response, 'Delete')

    # create

    def test_create_user_page_content(self):
        response = self.c.get(reverse('user:user-create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, _('First name'))
        self.assertContains(response, _('Last name'))
        self.assertContains(response, _('Username'))
        self.assertContains(response, _('Password'))
        self.assertContains(response, _('Confirm password'))
        self.assertContains(response, _('Join team (optional)'))
        self.assertContains(response, _('Team password'))
        self.assertContains(response, _('Signup'))
        self.assertRegex(
            response.content.decode('utf-8'),
            _(r'\bSign up\b'))

    def test_create_user_successfully(self):
        old_count = User.objects.count()
        response = self.c.post(reverse('user:user-create'),
                               self.user_data, follow=True)

        self.assertEqual(response.status_code, 200)

        new_count = User.objects.count()
        self.assertEqual(old_count + 1, new_count)

        user = User.objects.filter(username=self.user_data['username']).first()
        self.assertEqual(user.first_name, self.user_data['first_name'])
        self.assertEqual(user.last_name, self.user_data['last_name'])

        # user without team should redirect to tasks list
        self.assertRedirects(response, reverse('tasks:tasks-list'))

        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]), _('User created successfully'))

    def test_default_statuses_created_for_new_user_without_team(self):
        # count statuses before creating new user
        initial_status_count = Status.objects.count()
        initial_user_status_count = Status.objects.filter(
            creator=self.user).count()
        # create new user without team
        self.c.post(
            reverse('user:user-create'),
            self.user_data,
            follow=True
        )
        # get the newly created user
        new_user = User.objects.get(username=self.user_data['username'])
        # check status counts
        self.assertEqual(
            Status.objects.count(),
            # 6 default statuses should be added from statuses/models.py
            initial_status_count + 6
        )
        self.assertEqual(
            Status.objects.filter(creator=new_user).count(),
            6
        )
        # verify no statuses were created for the test user (self.user)
        self.assertEqual(
            Status.objects.filter(creator=self.user).count(),
            initial_user_status_count
        )

    def test_user_auto_login_after_create(self):
        self.c.logout()
        self.c.post(
            reverse('user:user-create'), self.user_data, follow=True)

        # check if user has been auto login
        user = User.objects.filter(username=self.user_data['username']).first()
        self.assertEqual(int(self.c.session['_auth_user_id']), user.pk)

    def test_create_user_without_team_redirect(self):
        response = self.c.post(
            reverse('user:user-create'), self.user_data, follow=True)
        self.assertEqual(response.status_code, 200)

        user = User.objects.filter(username=self.user_data['username']).first()
        self.assertIsNotNone(user)

        # check user has no team membership
        self.assertFalse(TeamMembership.objects.filter(user=user).exists())

        self.assertRedirects(response, reverse('tasks:tasks-list'))

    def test_check_for_not_create_user_with_same_username(self):
        self.c.post(
            reverse('user:user-create'), self.user_data, follow=True)
        users_count = User.objects.count()
        response = self.c.post(
            reverse('user:user-create'), self.user_data, follow=True)
        new_users_count = User.objects.count()
        self.assertEqual(users_count, new_users_count)
        self.assertNotEqual(response.status_code, 302)
        message = _('A user with that username already exists.')
        self.assertContains(response, message)

    def test_can_not_create_user_with_empty_name(self):
        self.user_data['username'] = ' '
        response = self.c.post(reverse('user:user-create'),
                               self.user_data, follow=True)
        self.assertFalse(User.objects.filter(username=" ").exists())
        message = _('This field is required.')
        self.assertContains(response, message)

    def test_create_user_password_do_not_match(self):
        user_data = self.user_data.copy()
        user_data['password2'] = 'different_password'

        response = self.c.post(
            reverse('user:user-create'), user_data, follow=True)

        # user does not created
        self.assertFalse(User.objects.filter(
            username=user_data['username']).exists())

        # validation error message
        self.assertContains(response, _("The entered passwords do not match."))

    def test_create_user_with_team_join_redirect(self):
        """test that creating user with team join redirects to tasks"""
        team = Team.objects.get(pk=1)
        user_data_with_team = self.user_data.copy()
        user_data_with_team.update({
            'join_team_name': team.name,
            'join_team_password': (
                'pbkdf2_sha256$260000$abcdefghijklmnopqrstuvwxyz123456'
            )
        })

        response = self.c.post(
            reverse('user:user-create'), user_data_with_team, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('tasks:tasks-list'))

        # check session has active team
        self.assertEqual(int(self.c.session['active_team_id']), team.id)

        # check welcome message with team info
        messages = list(get_messages(response.wsgi_request))
        team_messages = [
            str(msg) for msg in messages if 'joined team' in str(msg)
        ]
        self.assertEqual(len(team_messages), 1)

    def test_not_create_user_with_invalid_team_password(self):
        """test creating user with invalid team password"""
        team = Team.objects.get(pk=1)
        user_data_with_team = self.user_data.copy()
        user_data_with_team.update({
            'join_team_name': team.name,
            'join_team_password': 'wrongpassword'
        })

        response = self.c.post(
            reverse('user:user-create'), user_data_with_team, follow=True)

        # user should not be created without team membership
        self.assertEqual(response.status_code, 200)
        # user does not created
        self.assertFalse(User.objects.filter(
            username=self.user_data['username']).exists())

        # validation error message
        self.assertContains(response, _("Invalid team password"))
        user = User.objects.filter(username=self.user_data['username']).first()
        self.assertIsNone(user)

        # should not have team membership
        membership = TeamMembership.objects.filter(user=user, team=team).first()
        self.assertIsNone(membership)

    def test_not_create_user_with_nonexistent_team(self):
        """test creating user with nonexistent team"""
        user_data_with_team = self.user_data.copy()
        user_data_with_team.update({
            'join_team_name': 'Nonexistent Team',
            'join_team_password': 'somepassword'
        })

        response = self.c.post(
            reverse('user:user-create'), user_data_with_team, follow=True)

        # user should not be created without team membership
        self.assertEqual(response.status_code, 200)
        # user does not created
        self.assertFalse(User.objects.filter(
            username=self.user_data['username']).exists())

        # validation error message
        self.assertContains(response, _("Team with this name does not exist"))
        user = User.objects.filter(username=self.user_data['username']).first()
        self.assertIsNone(user)

        # should not have any team membership
        self.assertFalse(TeamMembership.objects.filter(user=user).exists())

    # update

    def test_update_user_status_200_and_check_content(self):
        response = self.c.get(
            reverse('user:user-update', args=[self.user.id]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, _('First name'))
        self.assertContains(response, _('Last name'))
        self.assertContains(response, _('Username'))
        self.assertContains(response, _('Password'))
        self.assertContains(response, _('Confirm password'))
        self.assertRegex(
            response.content.decode('utf-8'), _(r'\bEdit user\b'))
        self.assertRegex(
            response.content.decode('utf-8'), _(r'\bEdit\b'))
        self.assertContains(response, self.user.first_name)
        self.assertContains(response, self.user.last_name)
        self.assertContains(response, self.user.username)

    def test_update_user_successfully(self):
        response = self.c.post(
            reverse('user:user-update', args=[self.user.id]),
            self.user_data, follow=True)
        self.assertEqual(response.status_code, 200)

        self.assertRedirects(response, reverse('user:user-list'))

        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]), _('User updated successfully'))

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, self.user_data['first_name'])
        self.assertEqual(self.user.last_name, self.user_data['last_name'])
        self.assertEqual(self.user.username, self.user_data['username'])
        self.assertEqual(self.user.description, self.user_data['description'])
        self.assertTrue(
            check_password(self.user_data['password1'], self.user.password))

    def test_user_auto_login_after_update(self):
        self.c.post(
            reverse('user:user-update', args=[self.user.id]),
            self.user_data, follow=True)

        # check for user stay login
        self.assertEqual(int(self.c.session['_auth_user_id']), self.user.pk)

    def test_check_can_not_update_user_if_same_user_exist(self):
        new_user_data = {
            'first_name': 'New',
            'last_name': 'N',
            'username': 'me',  # username 'me' exists in test_users.json
            'password1': '222',
            'password2': '222',
            'join_team_name': '',
            'join_team_password': ''
        }
        response = self.c.post(
            reverse('user:user-update', args=[self.user.id]),
            new_user_data, follow=True)
        message = _('A user with that username already exists.')
        self.assertContains(response, message)
        self.assertNotEqual(response.status_code, 302)

    def test_can_not_set_empty_name_when_update_user(self):
        new_user_data = {
            'first_name': 'New',
            'last_name': 'N',
            'username': ' ',
            'password1': '222',
            'password2': '222',
            'join_team_name': '',
            'join_team_password': ''
        }
        response = self.c.post(
            reverse('user:user-update', args=[self.user.id]),
            new_user_data, follow=True)
        self.assertFalse(User.objects.filter(username=" ").exists())
        message = _('This field is required.')
        self.assertContains(response, message)

    def test_update_user_password_mismatch(self):
        user_data = self.user_data.copy()
        user_data['password2'] = 'different_password'

        response = self.c.post(
            reverse('user:user-update', args=[self.user.id]),
            user_data, follow=True)

        # check for validation error message
        self.assertContains(response, _("The entered passwords do not match."))
        self.assertNotEqual(response.status_code, 302)

    def test_update_user_with_team_join(self):
        """test updating user and joining a team"""
        team = Team.objects.get(pk=2)  # user is not admin of this team
        update_data = self.user_data.copy()
        update_data.update({
            'join_team_name': team.name,
            'join_team_password': (
                'pbkdf2_sha256$260000$abcdefghijklmnopqrstuvwxyz123456'
            )
        })

        response = self.c.post(
            reverse('user:user-update', args=[self.user.id]),
            update_data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('user:user-list'))

        # check user joined the team
        membership = TeamMembership.objects.filter(
            user=self.user, team=team).first()
        self.assertIsNotNone(membership)

        # check session updated
        self.assertEqual(int(self.c.session['active_team_id']), team.id)

        # check success message
        messages = list(get_messages(response.wsgi_request))
        success_messages = [
            str(msg) for msg in messages if 'joined team' in str(msg)
        ]
        self.assertEqual(len(success_messages), 1)

    def test_update_user_without_changing_password(self):
        """test updating user without changing password"""
        original_password = self.user.password
        update_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'username': 'updated_user',
            'password1': '',
            'password2': '',
            'join_team_name': '',
            'join_team_password': ''
        }

        response = self.c.post(
            reverse('user:user-update', args=[self.user.id]),
            update_data, follow=True)

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()

        # check fields updated
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.last_name, 'Name')
        self.assertEqual(self.user.username, 'updated_user')

        # password should remain unchanged
        self.assertEqual(self.user.password, original_password)

    def test_cancel_button_on_user_update_page(self):
        """Test Cancel button exists and redirects to user detail."""
        response = self.c.get(
            reverse('user:user-update', args=[self.user.id]),
            follow=True
        )

        self.assertEqual(response.status_code, 200)

        # Check that Cancel button with link to user-detail exists
        user_detail_url = reverse('user:user-detail', args=[self.user.id])
        self.assertContains(response, user_detail_url)

        # Check that Cancel button has correct text (translated)
        self.assertContains(response, _('Cancel'))

        # Test that clicking Cancel redirects to user detail page
        response = self.c.get(user_detail_url, follow=True)

        self.assertEqual(response.status_code, 200)
        # Should be on user detail page
        self.assertContains(response, self.user.username)
        response = self.c.get(
            reverse('user:user-update', args=[self.user.id]),
            follow=True
        )

        self.assertEqual(response.status_code, 200)

        # Check that Cancel button with link to user-list exists
        self.assertContains(response, reverse('user:user-list'))

        # Check that Cancel button has correct text (translated)
        self.assertContains(response, _('Cancel'))

        # Test that clicking Cancel redirects to user list
        # Find the Cancel link and follow it
        cancel_url = reverse('user:user-list')
        response = self.c.get(cancel_url, follow=True)

        self.assertEqual(response.status_code, 200)
        # Should be on user list page
        self.assertContains(response, _('Users'))

    # delete

    def test_get_delete_user_response_200_and_check_content(self):
        self.c.post(reverse('user:user-create'),
                    self.user_data, follow=True)
        new_user = User.objects.get(username="new")
        self.c.force_login(new_user)
        response = self.c.get(
            reverse('user:user-delete',
                    args=[new_user.id]), follow=False)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, _('Delete user'))
        self.assertContains(response, _('Yes, delete'))
        self.assertContains(response,
                            _('Are you sure you want to delete new?'))

    def test_delete_user_has_cancel_button(self):
        """Test that delete user page has a Cancel button."""
        self.c.post(reverse('user:user-create'),
                    self.user_data, follow=True)
        new_user = User.objects.get(username="new")
        self.c.force_login(new_user)
        response = self.c.get(
            reverse('user:user-delete',
                    args=[new_user.id]), follow=True)

        # Check that Cancel button exists
        self.assertContains(response, _('Cancel'))

    def test_delete_user_cancel_button_redirects_to_referer(self):
        """Test that Cancel button redirects to HTTP_REFERER."""
        self.c.post(reverse('user:user-create'),
                    self.user_data, follow=True)
        new_user = User.objects.get(username="new")
        self.c.force_login(new_user)

        # Set HTTP_REFERER in request
        response = self.c.get(
            reverse('user:user-delete', args=[new_user.id]),
            HTTP_REFERER=reverse('user:user-list'),
            follow=True
        )

        # Check that Cancel button is present
        self.assertContains(response, _('Cancel'))

        # The Cancel button href should contain the referer URL
        cancel_url = reverse('user:user-list')
        self.assertIn(cancel_url, response.content.decode('utf-8'))

    def test_delete_user_cancel_button_without_referer(self):
        """Test that Cancel button redirects to home when no referer."""
        self.c.post(reverse('user:user-create'),
                    self.user_data, follow=True)
        new_user = User.objects.get(username="new")
        self.c.force_login(new_user)

        # Request without HTTP_REFERER
        response = self.c.get(
            reverse('user:user-delete', args=[new_user.id]),
            follow=True
        )

        # Check that Cancel button exists and points to home
        self.assertContains(response, _('Cancel'))
        # Button href should be '/' when no referer
        self.assertIn('href="/"', response.content.decode('utf-8'))

    def test_delete_user_successfully(self):
        self.c.post(reverse('user:user-create'),
                    self.user_data, follow=True)
        user = User.objects.get(username="new")
        self.c.force_login(user)
        response = self.c.post(reverse('user:user-delete',
                                       args=[user.id]), follow=True)
        self.assertFalse(User.objects.filter(username="new").exists())
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('index'))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]),
                         _('User deleted successfully'))

    def test_can_not_delete_user_bound_with_task(self):
        response = self.c.get(reverse('user:user-delete',
                                      args=[self.user.id]), follow=True)
        self.assertTrue(User.objects.filter(username="he").exists())
        self.assertRedirects(response, reverse('user:user-list'))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]),
                         _('Cannot delete a user because it is in use'))

    def test_can_not_delete_user_being_team_admin(self):
        # create new user
        self.c.post(reverse('user:user-create'),
                    self.user_data, follow=True)
        new_user = User.objects.get(username="new")

        # create new team and make user admin
        team = Team.objects.create(
            name="New Test Team",
            description="Test team description",
            password="testpass123"
        )
        TeamMembership.objects.create(
            user=new_user,
            team=team,
            role='admin'
        )

        self.c.force_login(new_user)

        # try to delete new user
        response = self.c.get(reverse('user:user-delete',
                                      args=[new_user.id]), follow=True)

        # check that new user still exist
        self.assertTrue(User.objects.filter(username="new").exists())

        # check for redirect
        self.assertRedirects(response, reverse('user:user-list'))

        # check for error message
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(
            str(messages[0]),
            _(
                'Cannot delete user because they are admin '
                'of team(s): New Test Team. Transfer admin rights '
                'or delete the team(s) first.'
            )
        )

        # delete team after test
        team.delete()

    def test_can_join_existing_team(self):
        team = Team.objects.get(pk=1)
        new_user_data = {
            'first_name': 'Team',
            'last_name': 'Member',
            'username': 'team_member',
            'password1': '123',
            'password2': '123',
            'join_team_name': team.name,
            'join_team_password': (
                'pbkdf2_sha256$260000$abcdefghijklmnopqrstuvwxyz123456'
            )
        }
        response = self.c.post(reverse('user:user-create'),
                               new_user_data, follow=True)
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(username='team_member')

        # check membership was created
        membership = TeamMembership.objects.get(user=user, team=team)
        self.assertEqual(membership.role, 'member')

        # users who join a team should not get default statuses
        self.assertEqual(Status.objects.filter(creator=user).count(), 0)

    def test_delete_user_with_tasks_as_author(self):
        """test cannot delete user who is author of tasks"""
        # user 'me' (id=10) is author of tasks
        author_user = User.objects.get(username='me')
        self.c.force_login(author_user)

        response = self.c.get(reverse(
            'user:user-delete', args=[author_user.id]), follow=True)

        # should redirect and show error message
        self.assertRedirects(response, reverse('user:user-list'))
        messages = list(get_messages(response.wsgi_request))
        error_messages = [
            str(msg) for msg in messages if 'Cannot delete' in str(msg)
        ]
        self.assertEqual(len(error_messages), 1)

        # user should still exist
        self.assertTrue(User.objects.filter(username='me').exists())

    def test_delete_user_with_tasks_as_executor(self):
        """test cannot delete user who is executor of tasks"""
        # user 'he' (id=12) is executor of tasks
        executor_user = User.objects.get(username='he')

        response = self.c.get(reverse(
            'user:user-delete', args=[executor_user.id]), follow=True)

        # should redirect and show error message
        self.assertRedirects(response, reverse('user:user-list'))
        messages = list(get_messages(response.wsgi_request))
        error_messages = [
            str(msg) for msg in messages if 'Cannot delete' in str(msg)
        ]
        self.assertEqual(len(error_messages), 1)

        # user should still exist
        self.assertTrue(User.objects.filter(username='he').exists())
