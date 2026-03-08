from django.test import TestCase, Client
from django.urls import reverse
from task_manager.user.models import User
from task_manager.teams.models import Team, TeamMembership
from task_manager.tasks.models import Task
from task_manager.statuses.models import Status


class SoftDeleteEdgeCasesTestCase(TestCase):
    fixtures = [
        'tests/fixtures/test_users.json',
        'tests/fixtures/test_statuses.json',
        'tests/fixtures/test_teams.json',
        'tests/fixtures/test_teams_memberships.json'
    ]

    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.get(pk=10)  # 'me'
        self.other_user = User.objects.get(pk=12)  # 'he'
        self.team = Team.objects.get(pk=1)

    def test_soft_delete_promotes_new_admin(self):
        """Test soft deleting an admin promotes another member."""
        # Ensure 'me' is admin and 'he' is member in the same team
        TeamMembership.objects.filter(team=self.team).delete()
        TeamMembership.objects.create(
            user=self.admin_user,
            team=self.team,
            role='admin',
            status='active'
        )
        TeamMembership.objects.create(
            user=self.other_user,
            team=self.team,
            role='member',
            status='active'
        )

        self.admin_user.soft_delete()

        # Check 'he' is now admin
        membership = TeamMembership.objects.get(
            user=self.other_user,
            team=self.team
        )
        self.assertEqual(membership.role, 'admin')

        # Check 'me' membership is inactive
        old_membership = TeamMembership.objects.get(
            user=self.admin_user,
            team=self.team
        )
        self.assertEqual(old_membership.status, 'inactive')

    def test_soft_delete_removes_from_executors(self):
        """Test that soft deleted user is removed from task executors."""
        status = Status.objects.first()
        task = Task.objects.create(
            name="Test Task",
            author=self.other_user,
            status=status,
            team=self.team
        )
        task.executors.add(self.admin_user)
        self.assertIn(self.admin_user, task.executors.all())

        self.admin_user.soft_delete()

        self.assertNotIn(self.admin_user, task.executors.all())

    def test_soft_delete_keeps_author_as_is(self):
        """Test soft deleted user remains as author."""
        status = Status.objects.first()
        task = Task.objects.create(
            name="Author Task",
            author=self.admin_user,
            status=status,
            team=self.team
        )

        self.admin_user.soft_delete()

        task.refresh_from_db()
        # Since it's soft delete, the user object still exists.
        self.assertEqual(task.author, self.admin_user)
        self.assertTrue(task.author.is_deleted)

    def test_soft_delete_last_admin_deletes_team(self):
        """Test soft deleting the only admin deletes the team."""
        new_team = Team.objects.create(name="Solo Team", password="123")
        TeamMembership.objects.create(
            user=self.admin_user,
            team=new_team,
            role='admin',
            status='active'
        )

        self.admin_user.soft_delete()

        self.assertFalse(Team.objects.filter(id=new_team.id).exists())

    def test_soft_delete_display_name(self):
        """Test display_name property for soft deleted user."""
        self.assertEqual(self.admin_user.username, 'me')
        self.assertEqual(self.admin_user.display_name, 'me')

        self.admin_user.soft_delete()
        self.admin_user.refresh_from_db()

        # Check that display_name returns translated "Deleted user"
        from django.utils.translation import gettext as _
        self.assertEqual(self.admin_user.display_name, _('Deleted user'))
        self.assertNotEqual(
            self.admin_user.display_name,
            self.admin_user.username
        )

    def test_soft_deleted_user_list_view_context(self):
        """Test UserListView with soft deleted users and team membership."""
        self.client.force_login(self.admin_user)

        # Soft delete other user to see if they disappear from active lists
        self.other_user.soft_delete()

        response = self.client.get(reverse('user:user-list'))
        self.assertEqual(response.status_code, 200)

        # Soft deleted users should not be in the regular active list
        users = response.context['user_list']
        self.assertNotIn(self.other_user, users)
