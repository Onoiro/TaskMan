from django.test import TestCase
# from django.contrib.auth.models import User
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
