from django.test import TestCase
from task_manager.user.models import User
from task_manager.teams.models import Team, TeamMembership
from task_manager.user.forms import UserForm
from django.utils.translation import gettext as _


class UserFormTestCase(TestCase):
    fixtures = ["tests/fixtures/test_users.json",
                "tests/fixtures/test_teams.json",
                "tests/fixtures/test_teams_memberships.json",
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
            'join_team_name': '',
            'join_team_password': ''
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
            'join_team_name': '',
            'join_team_password': ''
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
        # Check user has no team memberships
        self.assertFalse(TeamMembership.objects.filter(user=user).exists())

    def test_join_existing_team(self):
        team = Team.objects.get(pk=1)
        form_data = {
            'first_name': 'Team',
            'last_name': 'Member',
            'username': 'new_team_member',
            'password1': '123',
            'password2': '123',
            'join_team_name': team.name,
            'join_team_password': 'pbkdf2_sha256$260000$abcdefghijklmnopqrstuvwxyz123456'
        }
        form = UserForm(data=form_data)
        self.assertTrue(form.is_valid())
        user = form.save()

        # Check membership was created
        membership = TeamMembership.objects.get(user=user, team=team)
        self.assertEqual(membership.role, 'member')

    def test_join_team_without_password_fails(self):
        team = Team.objects.get(pk=1)
        form_data = self.form_data.copy()
        form_data['join_team_name'] = team.name
        form_data['join_team_password'] = ''  # No password
        form = UserForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn(_("Team password is required when joining a team"),
                      form.errors['__all__'])

    def test_nonexistent_team_name(self):
        form_data = self.form_data.copy()
        form_data['join_team_name'] = 'Nonexistent Team'
        form_data['join_team_password'] = 'somepassword'
        form = UserForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn(_("Team with this name does not exist"),
                      form.errors['__all__'])

    def test_wrong_team_password(self):
        team = Team.objects.get(pk=1)
        form_data = self.form_data.copy()
        form_data['join_team_name'] = team.name
        form_data['join_team_password'] = 'wrongpassword'
        form = UserForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn(_("Invalid team password"), form.errors['__all__'])

    def test_update_user_shows_current_teams(self):
        # Get user with team membership
        user = User.objects.get(pk=10)  # me - has team membership
        form = UserForm(instance=user)

        # Check that current_teams field exists and is readonly
        self.assertIn('current_teams', form.fields)
        self.assertTrue('readonly' in form.fields['current_teams'].widget.attrs)

        # Check it shows correct team info
        expected_value = "Test Team (Admin), Another Test Team (Admin)"
        self.assertEqual(form.fields['current_teams'].initial, expected_value)

    def test_update_user_can_join_another_team(self):
        user = User.objects.get(pk=13)  # alone - no team
        new_team = Team.objects.get(pk=2)

        form_data = {
            'first_name': 'Updated',
            'last_name': 'User',
            'username': 'alone',
            'password1': '111',
            'password2': '111',
            'join_team_name': new_team.name,
            'join_team_password': 'pbkdf2_sha256$260000$abcdefghijklmnopqrstuvwxyz123456'
        }
        form = UserForm(data=form_data, instance=user)
        self.assertTrue(form.is_valid())
        updated_user = form.save()

        # Check membership was created
        self.assertTrue(TeamMembership.objects.filter(
            user=updated_user, team=new_team).exists())

    def test_update_user_cannot_join_same_team_twice(self):
        user = User.objects.get(pk=10)  # me - already in Test Team
        team = Team.objects.get(pk=1)

        form_data = {
            'first_name': 'Updated',
            'last_name': 'User',
            'username': 'me',
            'password1': '',
            'password2': '',
            'join_team_name': team.name,
            'join_team_password': 'pbkdf2_sha256$260000$abcdefghijklmnopqrstuvwxyz123456'
        }
        form = UserForm(data=form_data, instance=user)
        self.assertFalse(form.is_valid())
        self.assertIn(_("You are already a member of this team"),
                      form.errors['__all__'])

    def test_update_user_without_password(self):
        user = User.objects.get(pk=10)
        old_password_hash = user.password

        form_data = {
            'first_name': 'Updated Me',
            'last_name': 'Updated M',
            'username': 'me',
            'password1': '',
            'password2': '',
            'join_team_name': '',
            'join_team_password': ''
        }
        form = UserForm(data=form_data, instance=user)
        self.assertTrue(form.is_valid())
        updated_user = form.save()

        # Check that first_name was changed but not password
        self.assertEqual(updated_user.first_name, 'Updated Me')
        self.assertEqual(updated_user.password, old_password_hash)

    def test_update_user_with_new_password(self):
        user = User.objects.get(pk=10)
        old_password_hash = user.password

        form_data = {
            'first_name': 'Updated Me',
            'last_name': 'Updated M',
            'username': 'me',
            'password1': 'newpassword123',
            'password2': 'newpassword123',
            'join_team_name': '',
            'join_team_password': ''
        }
        form = UserForm(data=form_data, instance=user)
        self.assertTrue(form.is_valid())
        updated_user = form.save()

        # Check that password was changed
        self.assertNotEqual(updated_user.password, old_password_hash)
        self.assertTrue(updated_user.check_password('newpassword123'))

    def test_update_user_only_one_password_field_filled(self):
        user = User.objects.get(pk=10)

        # Entered only password1
        form_data = {
            'first_name': 'Updated Me',
            'last_name': 'Updated M',
            'username': 'me',
            'password1': 'newpassword123',
            'password2': '',
            'join_team_name': '',
            'join_team_password': ''
        }
        form = UserForm(data=form_data, instance=user)
        self.assertFalse(form.is_valid())
        self.assertIn(
            _("Both password fields must be filled or both left blank"),
            form.errors['__all__']
        )

        # Entered only password2
        form_data['password1'] = ''
        form_data['password2'] = 'newpassword123'
        form = UserForm(data=form_data, instance=user)
        self.assertFalse(form.is_valid())
        self.assertIn(
            _("Both password fields must be filled or both left blank"),
            form.errors['__all__']
        )

    def test_update_user_password_fields_not_required(self):
        user = User.objects.get(pk=10)
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
        form = UserForm()

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
        user = User.objects.get(pk=10)

        form_data = {
            'first_name': 'Updated Me',
            'last_name': 'Updated M',
            'username': 'me',
            'password1': '11',  # too short
            'password2': '11',
            'join_team_name': '',
            'join_team_password': ''
        }
        form = UserForm(data=form_data, instance=user)
        self.assertFalse(form.is_valid())
        self.assertIn(_(
            'Your password is too short.'
            ' It must contain at least 3 characters.'),
            form.errors['password1'])

    def test_update_user_passwords_mismatch_validation_works(self):
        user = User.objects.get(pk=10)

        form_data = {
            'first_name': 'Updated Me',
            'last_name': 'Updated M',
            'username': 'me',
            'password1': '123',
            'password2': '456',  # doesn't match
            'join_team_name': '',
            'join_team_password': ''
        }
        form = UserForm(data=form_data, instance=user)
        self.assertFalse(form.is_valid())
        self.assertIn(
            _('The entered passwords do not match.'),
            form.errors['password2'])
