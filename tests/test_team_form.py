from django.test import TestCase
from task_manager.teams.models import Team, TeamMembership
from task_manager.teams.forms import TeamForm
from django.utils.translation import gettext as _
from django.contrib.auth import get_user_model

User = get_user_model()


class TeamFormTestCase(TestCase):
    fixtures = ["tests/fixtures/test_users.json",
                "tests/fixtures/test_teams.json",
                "tests/fixtures/test_teams_memberships.json",
             ]

    def setUp(self):
        self.form_data = {
            'name': 'New Team',
            'description': 'This is a new test team',
            'password1': '111',
            'password2': '111'
        }
        self.user = User.objects.get(pk=10)

    def test_TeamForm_valid(self):
        form = TeamForm(data=self.form_data)
        self.assertTrue(form.is_valid())

    def test_password_too_short(self):
        form_data = self.form_data.copy()
        form_data['password1'] = '11'
        form_data['password2'] = '11'
        form = TeamForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn(_(
            'Your password is too short.'
            ' It must contain at least 3 characters.'),
            form.errors['password1'])

    def test_passwords_do_not_match(self):
        form_data = self.form_data.copy()
        form_data['password1'] = '111'
        form_data['password2'] = '222'
        form = TeamForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn(
            _('The entered passwords do not match.'),
            form.errors['password2'])

    def test_required_fields(self):
        # check for required fields
        form = TeamForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        self.assertIn('password1', form.errors)
        self.assertIn('password2', form.errors)
        # check field may not required
        form_data = self.form_data.copy()
        form_data.pop('description')
        form = TeamForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_save_team(self):
        form = TeamForm(data=self.form_data)
        self.assertTrue(form.is_valid())
        team = form.save(commit=True)
        
        # Create admin membership for the team
        TeamMembership.objects.create(
            user=self.user,
            team=team,
            role='admin'
        )

        # check team saved correct
        self.assertIsInstance(team, Team)
        self.assertEqual(team.name, 'New Team')
        self.assertEqual(team.description, 'This is a new test team')
        
        # Check that user is admin of the team through membership
        membership = TeamMembership.objects.get(user=self.user, team=team)
        self.assertEqual(membership.role, 'admin')
        
        # check password saved
        self.assertTrue(team.password)

    def test_team_name_uniqueness(self):
        # check for team name is unique
        existing_team_name = "Test Team"  # this name exists in fixtures
        form_data = self.form_data.copy()
        form_data['name'] = existing_team_name
        form = TeamForm(data=form_data)

        # Django автоматически проверяет уникальность полей модели
        # с unique=True, поэтому форма должна быть невалидной
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_update_team(self):
        # check for update existing team
        team = Team.objects.get(pk=1)
        
        # Get original admin of the team
        original_admin_membership = TeamMembership.objects.filter(
            team=team, role='admin'
        ).first()
        
        form_data = {
            'name': 'Updated Team Name',
            'description': 'Updated team description',
            'password1': '456',
            'password2': '456'
        }
        form = TeamForm(data=form_data, instance=team)
        self.assertTrue(form.is_valid())
        updated_team = form.save()

        # check data was updated
        self.assertEqual(updated_team.name, 'Updated Team Name')
        self.assertEqual(updated_team.description, 'Updated team description')
        self.assertEqual(updated_team.password, '456')

        # check that team admin membership still exists
        if original_admin_membership:
            updated_admin_membership = TeamMembership.objects.filter(
                team=updated_team, role='admin'
            ).first()
            self.assertIsNotNone(updated_admin_membership)
            self.assertEqual(
                updated_admin_membership.user, 
                original_admin_membership.user
            )
        
        # check that created_at still the same
        self.assertEqual(updated_team.created_at, team.created_at)

    def test_form_help_texts(self):
        # check for correct help text available
        form = TeamForm()
        self.assertEqual(
            form.fields['password1'].help_text,
            _("Your password must contain at least 3 characters.")
        )
        self.assertEqual(
            form.fields['password2'].help_text,
            _("Please enter your password one more time")
        )

    def test_form_labels(self):
        # check for correct labels
        form = TeamForm()
        self.assertEqual(form.fields['password1'].label, _('Password'))
        self.assertEqual(form.fields['password2'].label, _('Confirm password'))
