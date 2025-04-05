from django import forms
from django.test import TestCase
from task_manager.user.models import User
from task_manager.teams.models import Team
from task_manager.user.forms import UserForm
from django.utils.translation import gettext as _


class UserFormTestCase(TestCase):
    fixtures = ["tests/fixtures/test_teams.json",
                "tests/fixtures/test_users.json",
                "tests/fixtures/test_tasks.json",
                "tests/fixtures/test_statuses.json",
                "tests/fixtures/test_labels.json"]

    def setUp(self):
        self.form_data = {
            'first_name': 'Him',
            'last_name': 'H',
            'username': 'him',
            'password1': '111',
            'password2': '111',
            'is_team_admin': True,
            'team_name': ''
        }

    def test_UserForm_valid(self):
        form = UserForm(data=self.form_data)
        self.assertTrue(form.is_valid())

    def test_password_too_short(self):
        form_data = {
            'username': 'user',
            'password1': '11',
            'password2': '11'}
        form = UserForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn(_(
            'Your password is too short.'
            ' It must contain at least 3 characters.'),
            form.errors['password1'])

    def test_passwords_do_not_match(self):
        form_data = {
            'username': 'user',
            'password1': '111',
            'password2': '222'}
        form = UserForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn(
            _('The entered passwords do not match.'),
            form.errors['password2'])

    def test_save_user(self):
        form = UserForm(data=self.form_data)
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertIsInstance(user, User)
        self.assertTrue(user.check_password('111'))
        self.assertEqual(user.username, 'him')
        self.assertTrue(user.is_team_admin)

    def test_join_existing_team(self):
        team = Team.objects.get(pk=1)
        form_data = {
            'first_name': 'Team',
            'last_name': 'Member',
            'username': 'team_member',
            'password1': '123',
            'password2': '123',
            'is_team_admin': False,
            'team_name': team.name
        }
        form = UserForm(data=form_data)
        self.assertTrue(form.is_valid())
        user = form.save()
        self.assertEqual(user.team, team)
        self.assertFalse(user.is_team_admin)

    def test_neither_team_admin_nor_team_name(self):
        # verifies that the form is invalid if the user
        # has not selected the team-admin role and specified a team name
        form_data = self.form_data.copy()
        form_data['is_team_admin'] = False
        form_data['team_name'] = ''
        form = UserForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn(
            _("You must either register as team admin or specify team name"),
            form.errors['__all__'])

    def test_both_team_admin_and_team_name(self):
        # verifies that the form is invalid if the user
        # has selected the team-admin role and specified a team name
        form_data = self.form_data.copy()
        form_data['is_team_admin'] = True
        form_data['team_name'] = 'Test Team'
        form = UserForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn(_("You can't be team admin and"
                      " join existing team at the same time"),
                      form.errors['__all__'])

    def test_nonexistent_team_name(self):
        # The test verifies that the form is invalid
        # if a non-existent team name is specified
        form_data = self.form_data.copy()
        form_data['is_team_admin'] = False
        form_data['team_name'] = 'Nonexistent Team'
        form = UserForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn(_("There is no such team"), form.errors['__all__'])

    def test_update_user_preserves_team(self):
        # verifies that when a user updates
        # a user with a command, the command is preserved
        user = User.objects.get(pk=10)  # me - is_team_admin
        team = Team.objects.get(pk=1)  # Test Team
        user.team = team
        user.save()

        form_data = {
            'first_name': 'Updated Me',
            'last_name': 'Updated M',
            'username': 'me',
            'password1': '111',
            'password2': '111',
        }
        form = UserForm(data=form_data, instance=user)
        self.assertTrue(form.is_valid())
        updated_user = form.save()
        self.assertEqual(updated_user.team, team)
        self.assertEqual(updated_user.is_team_admin, True)

    def test_edit_user_fields_readonly(self):
        # checks that the team_name field becomes readonly when editing a user
        user = User.objects.get(pk=10)  # me - is_team_admin
        team = Team.objects.get(pk=1)  # Test Team
        user.team = team
        user.save()

        form = UserForm(instance=user)
        self.assertEqual(form.initial['team_name'], team.name)
        self.assertTrue('readonly' in form.fields['team_name'].widget.attrs)
        self.assertIsInstance(
            form.fields['is_team_admin'].widget,
            forms.HiddenInput)

    def test_update_user_with_no_team(self):
        # verifies that when a user updates without the team,
        # the form works correctly
        user = User.objects.get(pk=12)  # he - user without the team
        form_data = {
            'first_name': 'Updated He',
            'last_name': 'Updated H',
            'username': 'he',
            'password1': '111',
            'password2': '111',
        }
        form = UserForm(data=form_data, instance=user)
        self.assertTrue(form.is_valid())
        updated_user = form.save()
        self.assertIsNone(updated_user.team)
        self.assertFalse(updated_user.is_team_admin)

    def test_update_user_with_team_and_changing_other_fields(self):
        # verifies that when you update a user with a command,
        # you can change other fields but not the command or role
        user = User.objects.get(pk=12)  # he
        team = Team.objects.get(pk=1)  # Test Team
        user.team = team
        user.save()

        # try to update user data
        form_data = {
            'first_name': 'New Name',
            'last_name': 'New Last',
            'username': 'he',
            'password1': '123',
            'password2': '123',
            'team_name': 'Another Test Team',  # try change team
            'is_team_admin': True,  # try set user as team admin
        }
        form = UserForm(data=form_data, instance=user)
        self.assertTrue(form.is_valid())
        updated_user = form.save()

        # check for updated first and last names
        self.assertEqual(updated_user.first_name, 'New Name')
        self.assertEqual(updated_user.last_name, 'New Last')

        # check for team name and user status still the same
        self.assertEqual(updated_user.team, team)
        self.assertFalse(updated_user.is_team_admin)
