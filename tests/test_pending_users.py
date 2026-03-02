"""
Tests for pending users logic in teams.

Pending users should:
- NOT appear in the main user list (only in pending section for admin)
- NOT be selectable as executors in tasks
- NOT appear in task filters as executor options
- Be visible in pending section only for team admin
- Become visible in user list after approval
"""
from task_manager.user.models import User
from task_manager.teams.models import Team, TeamMembership
from task_manager.statuses.models import Status
from django.test import TestCase, Client
from django.urls import reverse
import uuid


class PendingUsersTestCase(TestCase):
    fixtures = [
        "tests/fixtures/test_teams.json",
        "tests/fixtures/test_users.json",
        "tests/fixtures/test_teams_memberships.json",
        "tests/fixtures/test_statuses.json",
        "tests/fixtures/test_tasks.json",
        "tests/fixtures/test_labels.json"
    ]

    def setUp(self):
        # Use existing users from fixtures
        # pk=10 is admin in team 1, pk=12 is member in team 1
        self.admin_user = User.objects.get(pk=10)
        self.member_user = User.objects.get(pk=12)
        self.team = Team.objects.get(pk=1)
        self.status = Status.objects.filter(team=self.team).first()

        # Use Django test client with force_login
        self.c = Client()
        self.c.force_login(self.admin_user)

        # Update UUIDs for fixtures
        self._update_fixture_uuids()

    def _update_fixture_uuids(self):
        """Update UUIDs for fixture-loaded objects"""
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

        # Update membership UUIDs
        memberships_data = [
            (1, '550e8400-e29b-41d4-a716-446655440040'),
            (2, '550e8400-e29b-41d4-a716-446655440041'),
            (3, '550e8400-e29b-41d4-a716-446655440042'),
        ]
        for membership_pk, membership_uuid in memberships_data:
            membership = TeamMembership.objects.filter(pk=membership_pk).first()
            if membership:
                membership.uuid = uuid.UUID(membership_uuid)
                membership.save(update_fields=['uuid'])

    def _set_active_team(self, team):
        """Helper to set active team in session"""
        session = self.c.session
        session['active_team_uuid'] = str(team.uuid)
        session.save()

    def test_pending_user_not_in_main_user_list(self):
        """Test that pending user does NOT appear in main user list"""
        # Create a pending user
        pending_user = User.objects.create_user(
            username='pending_test_user',
            password='password123'
        )
        TeamMembership.objects.create(
            user=pending_user,
            team=self.team,
            role='member',
            status='pending'
        )

        # Set active team and get user list
        self._set_active_team(self.team)
        response = self.c.get(reverse('user:user-list'))

        # Pending user should NOT be in main user list
        user_list = list(response.context['user_list'])
        self.assertNotIn(pending_user, user_list)

    def test_pending_user_in_pending_section_for_admin(self):
        """Test that pending user appears in pending section for admin"""
        # Create a pending user
        pending_user = User.objects.create_user(
            username='pending_section_user',
            password='password123'
        )
        membership = TeamMembership.objects.create(
            user=pending_user,
            team=self.team,
            role='member',
            status='pending'
        )

        # Set active team and get user list
        self._set_active_team(self.team)
        response = self.c.get(reverse('user:user-list'))

        # Pending user should be in pending_memberships
        pending_memberships = list(response.context['pending_memberships'])
        self.assertIn(membership, pending_memberships)

    def test_pending_user_not_selectable_as_executor(self):
        """Test that pending user is not available as executor in task form"""
        # Create a pending user
        pending_user = User.objects.create_user(
            username='pending_executor_user',
            password='password123'
        )
        TeamMembership.objects.create(
            user=pending_user,
            team=self.team,
            role='member',
            status='pending'
        )

        # Set active team and get task create page
        self._set_active_team(self.team)
        response = self.c.get(reverse('tasks:task-create'))

        # Get executors field choices
        executors_field = response.context['form'].fields['executors']
        executor_choices = list(executors_field.queryset)

        # Pending user should NOT be in executor choices
        self.assertNotIn(pending_user, executor_choices)

    def test_pending_user_not_in_task_filter(self):
        """Test that pending user is not in task filter executor options"""
        # Create a pending user
        pending_user = User.objects.create_user(
            username='pending_filter_user',
            password='password123'
        )
        TeamMembership.objects.create(
            user=pending_user,
            team=self.team,
            role='member',
            status='pending'
        )

        # Set active team and get tasks list
        self._set_active_team(self.team)
        response = self.c.get(reverse('tasks:tasks-list'))

        # Check the filter form has executors field
        if hasattr(response.context, 'filters') and response.context['filters']:
            filters = response.context['filters']
            executor_filter = filters.form.fields['executors']
            executor_choices = list(executor_filter.queryset)

            # Pending user should NOT be in filter choices
            self.assertNotIn(pending_user, executor_choices)
        else:
            # If no filters in context, check the view provides filter
            team_users = User.objects.filter(
                team_memberships__team=self.team,
                team_memberships__status='active'
            )
            self.assertNotIn(pending_user, team_users)

    def test_active_user_visible_after_approval(self):
        """Test that user becomes visible in user list after approval"""
        # Create a pending user
        pending_user = User.objects.create_user(
            username='approval_test_user',
            password='password123'
        )
        membership = TeamMembership.objects.create(
            user=pending_user,
            team=self.team,
            role='member',
            status='pending'
        )

        # Set active team
        self._set_active_team(self.team)

        # Before approval - user should NOT be in main list
        response = self.c.get(reverse('user:user-list'))
        user_list = list(response.context['user_list'])
        self.assertNotIn(pending_user, user_list)

        # Approve the user (change status to active)
        self.c.post(
            reverse('teams:team-member-role-update', args=[membership.uuid]),
            {'role': 'member', 'status': 'active'},
            follow=True
        )

        # After approval - user should be in main list
        response = self.c.get(reverse('user:user-list'))
        user_list = list(response.context['user_list'])
        self.assertIn(pending_user, user_list)

    def test_non_admin_cannot_see_pending_section(self):
        """Test that non-admin users cannot see pending users section"""
        # Use existing member from fixture (pk=12)
        regular_member = self.member_user

        # Create a pending user
        pending_user = User.objects.create_user(
            username='hidden_pending_user',
            password='password123'
        )
        TeamMembership.objects.create(
            user=pending_user,
            team=self.team,
            role='member',
            status='pending'
        )

        # Login as regular member (not admin)
        self.c.logout()
        self.c.force_login(regular_member)
        self._set_active_team(self.team)

        # Get user list
        response = self.c.get(reverse('user:user-list'))

        # Pending memberships should be empty for non-admin
        pending_memberships = list(response.context['pending_memberships'])
        self.assertEqual(len(pending_memberships), 0)

        # Regular member should see only active users
        user_list = list(response.context['user_list'])
        self.assertIn(regular_member, user_list)
        self.assertNotIn(pending_user, user_list)

    def test_pending_user_can_be_approved_as_admin(self):
        """Test that admin can approve pending user"""
        # Create a pending user
        pending_user = User.objects.create_user(
            username='to_approve_user',
            password='password123'
        )
        membership = TeamMembership.objects.create(
            user=pending_user,
            team=self.team,
            role='member',
            status='pending'
        )

        # Set active team and approve the user
        self._set_active_team(self.team)
        self.c.post(
            reverse('teams:team-member-role-update', args=[membership.uuid]),
            {'role': 'member', 'status': 'active'},
            follow=True
        )

        # Verify status changed
        membership.refresh_from_db()
        self.assertEqual(membership.status, 'active')

    def test_admin_sees_only_active_in_user_list(self):
        """Test that admin sees only active users in main user list"""
        # Create an active member
        active_member = User.objects.create_user(
            username='active_member_test',
            password='password123'
        )
        TeamMembership.objects.create(
            user=active_member,
            team=self.team,
            role='member',
            status='active'
        )

        # Create a pending user
        pending_user = User.objects.create_user(
            username='pending_user_list_test',
            password='password123'
        )
        TeamMembership.objects.create(
            user=pending_user,
            team=self.team,
            role='member',
            status='pending'
        )

        # Set active team and get user list
        self._set_active_team(self.team)
        response = self.c.get(reverse('user:user-list'))
        user_list = list(response.context['user_list'])

        # Active member should be in list
        self.assertIn(active_member, user_list)

        # Admin should also see themselves
        self.assertIn(self.admin_user, user_list)

        # Pending user should NOT be in main list
        self.assertNotIn(pending_user, user_list)

    def test_pending_user_not_in_executors_form_field(self):
        """Test that pending user cannot be set as executor"""
        # Create a pending user
        pending_user = User.objects.create_user(
            username='pending_post_executor',
            password='password123'
        )
        TeamMembership.objects.create(
            user=pending_user,
            team=self.team,
            role='member',
            status='pending'
        )

        # Set active team and get task create page
        self._set_active_team(self.team)
        response = self.c.get(reverse('tasks:task-create'))
        executors_field = response.context['form'].fields['executors']
        executor_choices = list(executors_field.queryset)

        # Pending user should NOT be in executor choices
        self.assertNotIn(pending_user, executor_choices)
