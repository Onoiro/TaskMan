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

    def test_create_user_without_password_fails(self):
        form_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'username': 'testuser',
            'password1': '',
            'password2': '',
            'is_team_admin': False,
            'team_name': ''
        }
        form = UserForm(data=form_data)
        self.assertFalse(form.is_valid())
        # password fields required when create user
        self.assertIn('password1', form.errors)
        self.assertIn('password2', form.errors)

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

    def test_both_team_admin_and_team_name(self):
        # verifies that the form is invalid if the user
        # has selected the team-admin role and specified a team name
        form_data = self.form_data.copy()
        form_data['is_team_admin'] = True
        form_data['team_name'] = 'Test Team'
        form = UserForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn(_("You can't signup as team admin and"
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

    def test_update_team_admin_hidden_team_name_field(self):
        # check team_name field hidden when team_admin updating
        user = User.objects.get(pk=10)  # me - is_team_admin
        user.team = None  # shure user have no team
        user.save()

        form = UserForm(instance=user)
        self.assertIsInstance(
            form.fields['team_name'].widget, forms.HiddenInput)
        self.assertTrue(form.initial['is_team_admin'])

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
        user = User.objects.get(pk=13)  # he - user without the team
        form_data = {
            'first_name': 'Updated He',
            'last_name': 'Updated H',
            'username': 'alone',
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

    def test_update_user_without_password(self):
        # check if user can update without enter password
        user = User.objects.get(pk=10)  # me - is_team_admin
        old_password_hash = user.password

        form_data = {
            'first_name': 'Updated Me',
            'last_name': 'Updated M',
            'username': 'me',
            'password1': '',  # empty password field
            'password2': '',  # empty password2 field
        }
        form = UserForm(data=form_data, instance=user)
        # short password validation skipped when empty and form is valid
        # mismatch validation skipped when empty
        self.assertTrue(form.is_valid())
        updated_user = form.save()

        # check that first_name was changed but not passwrd
        self.assertEqual(updated_user.first_name, 'Updated Me')
        self.assertEqual(updated_user.password, old_password_hash)

    def test_update_user_with_new_password(self):
        # check that user can change password when update
        user = User.objects.get(pk=10)  # me - is_team_admin
        old_password_hash = user.password

        form_data = {
            'first_name': 'Updated Me',
            'last_name': 'Updated M',
            'username': 'me',
            'password1': 'newpassword123',
            'password2': 'newpassword123',
        }
        form = UserForm(data=form_data, instance=user)
        self.assertTrue(form.is_valid())
        updated_user = form.save()

        # check that password was changed
        self.assertNotEqual(updated_user.password, old_password_hash)
        self.assertTrue(updated_user.check_password('newpassword123'))

    def test_update_user_only_one_password_field_filled(self):
        # check for validation error when only one password field is entered
        user = User.objects.get(pk=10)  # me - is_team_admin

        # entered only password1
        form_data = {
            'first_name': 'Updated Me',
            'last_name': 'Updated M',
            'username': 'me',
            'password1': 'newpassword123',
            'password2': '',  # empty field
        }
        form = UserForm(data=form_data, instance=user)
        self.assertFalse(form.is_valid())
        self.assertIn(
            _("Both password fields must be filled or both left blank"),
            form.errors['__all__']
        )

        # entered only password1
        form_data['password1'] = ''  # empty field
        form_data['password2'] = 'newpassword123'
        form = UserForm(data=form_data, instance=user)
        self.assertFalse(form.is_valid())
        self.assertIn(
            _("Both password fields must be filled or both left blank"),
            form.errors['__all__']
        )

    def test_update_user_password_fields_not_required(self):
        user = User.objects.get(pk=10)  # me - is_team_admin
        form = UserForm(instance=user)

        self.assertFalse(form.fields['password1'].required)
        self.assertFalse(form.fields['password2'].required)
        self.assertEqual(
            form.fields['password1'].help_text,
            _("Leave blank if you don't want to change password")
        )
        self.assertEqual(
            form.fields['password2'].help_text,
            _("Leave blank if you don't want to change password")
        )

    def test_create_user_password_fields_required(self):
        form = UserForm()  # no instance - this is creating user

        self.assertTrue(form.fields['password1'].required)
        self.assertTrue(form.fields['password2'].required)
        self.assertEqual(
            form.fields['password1'].help_text,
            _("Your password must contain at least 3 characters.")
        )
        self.assertEqual(
            form.fields['password2'].help_text,
            _("Please enter your password one more time")
        )

    def test_update_user_short_password_validation_applied(self):
        # if passwords entered short password validation works
        user = User.objects.get(pk=10)  # me - is_team_admin

        form_data = {
            'first_name': 'Updated Me',
            'last_name': 'Updated M',
            'username': 'me',
            'password1': '11',  # too short
            'password2': '11',
        }
        form = UserForm(data=form_data, instance=user)
        self.assertFalse(form.is_valid())
        self.assertIn(_(
            'Your password is too short.'
            ' It must contain at least 3 characters.'),
            form.errors['password1'])

    def test_update_user_passwords_mismatch_validation_works(self):
        # if passwords entered mismatch validation works
        user = User.objects.get(pk=10)  # me - is_team_admin

        form_data = {
            'first_name': 'Updated Me',
            'last_name': 'Updated M',
            'username': 'me',
            'password1': '123',
            'password2': '456',  # doesn't match
        }
        form = UserForm(data=form_data, instance=user)
        self.assertFalse(form.is_valid())
        self.assertIn(
            _('The entered passwords do not match.'),
            form.errors['password2'])
