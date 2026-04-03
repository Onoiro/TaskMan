"""
Tests for limit service and limit checks in views.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.messages import get_messages

from task_manager.user.models import User
from task_manager.teams.models import Team, TeamMembership
from task_manager.tasks.models import Task, ChecklistItem
from task_manager.statuses.models import Status
from task_manager.limit_service import LimitService


class LimitServiceTasksTest(TestCase):
    """Tests for task limit checking."""

    fixtures = ["tests/fixtures/test_users.json",
                "tests/fixtures/test_teams.json",
                "tests/fixtures/test_teams_memberships.json",
                "tests/fixtures/test_statuses.json"]

    def setUp(self):
        self.user = User.objects.get(username='me')
        self.service = LimitService(self.user)
        # Create a personal status for testing
        self.status = Status.objects.create(
            name='Test Status',
            creator=self.user,
            team=None,
            color='#ffffff'
        )

    def test_new_user_can_create_task(self):
        """New user with 0 tasks can create task."""
        result = self.service.can_create_task()
        self.assertTrue(result.allowed)
        self.assertEqual(result.current, 0)

    def test_cannot_exceed_task_limit(self):
        """Cannot create task when 500 personal tasks exist."""
        # Create 500 personal tasks
        tasks = [
            Task(
                name=f'task_{i}',
                author=self.user,
                team=None,
                status=self.status
            )
            for i in range(500)
        ]
        Task.objects.bulk_create(tasks)

        result = self.service.can_create_task()
        self.assertFalse(result.allowed)
        self.assertEqual(result.current, 500)

    def test_task_limit_counts_team_tasks(self):
        """Task limit counts team tasks."""
        # Create team and add user as admin
        team = Team.objects.create(
            name='Test Team Limit',
            password='test'
        )
        TeamMembership.objects.create(
            user=self.user,
            team=team,
            role='admin',
            status='active'
        )
        # Create a team status
        team_status = Status.objects.create(
            name='Team Status',
            creator=self.user,
            team=team,
            color='#ff0000'
        )

        # Create 500 tasks in the team
        tasks = [
            Task(
                name=f'team_task_{i}',
                author=self.user,
                team=team,
                status=team_status
            )
            for i in range(500)
        ]
        Task.objects.bulk_create(tasks)

        result = self.service.can_create_task()
        self.assertFalse(result.allowed)
        self.assertEqual(result.current, 500)

    def test_task_limit_is_cross_team(self):
        """Task limit is cross-team (personal + team tasks)."""
        # Create team and add user as admin
        team = Team.objects.create(
            name='Test Team Cross',
            password='test'
        )
        TeamMembership.objects.create(
            user=self.user,
            team=team,
            role='admin',
            status='active'
        )

        # Create a team status
        team_status = Status.objects.create(
            name='Cross Team Status',
            creator=self.user,
            team=team,
            color='#00ff00'
        )

        # Create 250 personal tasks
        personal_tasks = [
            Task(
                name=f'personal_task_{i}',
                author=self.user,
                team=None,
                status=self.status
            )
            for i in range(250)
        ]
        Task.objects.bulk_create(personal_tasks)

        # Create 250 team tasks
        team_tasks = [
            Task(
                name=f'team_task_{i}',
                author=self.user,
                team=team,
                status=team_status
            )
            for i in range(250)
        ]
        Task.objects.bulk_create(team_tasks)

        result = self.service.can_create_task()
        self.assertFalse(result.allowed)
        self.assertEqual(result.current, 500)

    def test_task_limit_499_still_allowed(self):
        """499 tasks still allowed (limit is 500)."""
        # Create 499 personal tasks
        tasks = [
            Task(
                name=f'task_{i}',
                author=self.user,
                team=None,
                status=self.status
            )
            for i in range(499)
        ]
        Task.objects.bulk_create(tasks)

        result = self.service.can_create_task()
        self.assertTrue(result.allowed)
        self.assertEqual(result.current, 499)

    def test_limit_message_contains_max(self):
        """Limit message contains max value."""
        # Create 500 tasks to reach limit
        tasks = [
            Task(
                name=f'task_{i}',
                author=self.user,
                team=None,
                status=self.status
            )
            for i in range(500)
        ]
        Task.objects.bulk_create(tasks)

        result = self.service.can_create_task()
        self.assertIn('500', result.message)


class LimitServiceTeamsTest(TestCase):
    """Tests for team limit checking."""

    fixtures = ["tests/fixtures/test_users.json",
                "tests/fixtures/test_teams.json",
                "tests/fixtures/test_teams_memberships.json",
                "tests/fixtures/test_statuses.json"]

    def setUp(self):
        self.user = User.objects.get(username='me')
        # Count existing teams where user is admin from fixtures
        self.initial_teams = TeamMembership.objects.filter(
            user=self.user,
            role='admin'
        ).count()
        self.service = LimitService(self.user)

    def test_can_create_first_team(self):
        """User can create team if under limit."""
        result = self.service.can_create_team()
        self.assertTrue(result.allowed)
        # Current should equal initial teams from fixtures
        self.assertEqual(result.current, self.initial_teams)

    def test_cannot_exceed_team_limit(self):
        """Cannot create more than 3 teams."""
        # Calculate how many more teams we need to create
        teams_to_create = 3 - self.initial_teams

        # Create teams where user is admin
        for i in range(teams_to_create):
            team = Team.objects.create(
                name=f'New Team Limit {i}',
                password='test'
            )
            TeamMembership.objects.create(
                user=self.user,
                team=team,
                role='admin',
                status='active'
            )

        result = self.service.can_create_team()
        self.assertFalse(result.allowed)
        self.assertEqual(result.current, 3)

    def test_member_not_counted_as_owner(self):
        """Team member (not admin) is not counted as owner."""
        # Create team by another user (pk=11 is admin in fixtures)
        other_user = User.objects.get(pk=11)
        team = Team.objects.create(
            name='Team Member Test',
            password='test'
        )
        TeamMembership.objects.create(
            user=other_user,
            team=team,
            role='admin',
            status='active'
        )
        # Add self.user as member (not admin)
        TeamMembership.objects.create(
            user=self.user,
            team=team,
            role='member',
            status='active'
        )

        result = self.service.can_create_team()
        # Current should still be initial_teams (member doesn't count)
        self.assertEqual(result.current, self.initial_teams)


class LimitServiceChecklistTest(TestCase):
    """Tests for checklist item limit checking."""

    fixtures = ["tests/fixtures/test_users.json",
                "tests/fixtures/test_teams.json",
                "tests/fixtures/test_teams_memberships.json",
                "tests/fixtures/test_statuses.json"]

    def setUp(self):
        self.user = User.objects.get(username='me')
        self.service = LimitService(self.user)
        # Create a personal status for testing
        self.status = Status.objects.create(
            name='Checklist Test Status',
            creator=self.user,
            team=None,
            color='#ffffff'
        )
        # Create a task for testing
        self.task = Task.objects.create(
            name='Checklist Test Task',
            author=self.user,
            team=None,
            status=self.status
        )

    def test_can_add_checklist_item(self):
        """Can add checklist item when task has 0 items."""
        result = self.service.can_add_checklist_item(self.task)
        self.assertTrue(result.allowed)
        self.assertEqual(result.current, 0)

    def test_cannot_exceed_checklist_limit(self):
        """Cannot add more than 20 checklist items."""
        # Create 20 checklist items
        items = [
            ChecklistItem(
                task=self.task,
                text=f'Item {i}',
                position=i
            )
            for i in range(20)
        ]
        ChecklistItem.objects.bulk_create(items)

        result = self.service.can_add_checklist_item(self.task)
        self.assertFalse(result.allowed)
        self.assertEqual(result.current, 20)

    def test_checklist_limit_19_still_allowed(self):
        """19 checklist items still allowed."""
        # Create 19 checklist items
        items = [
            ChecklistItem(
                task=self.task,
                text=f'Item {i}',
                position=i
            )
            for i in range(19)
        ]
        ChecklistItem.objects.bulk_create(items)

        result = self.service.can_add_checklist_item(self.task)
        self.assertTrue(result.allowed)
        self.assertEqual(result.current, 19)


class LimitCheckInViewsTest(TestCase):
    """Tests for limit checking in views."""

    fixtures = ["tests/fixtures/test_users.json",
                "tests/fixtures/test_teams.json",
                "tests/fixtures/test_teams_memberships.json",
                "tests/fixtures/test_statuses.json",
                "tests/fixtures/test_tasks.json",
                "tests/fixtures/test_labels.json"]

    def setUp(self):
        self.user = User.objects.get(username='me')
        self.c = Client()
        self.c.force_login(self.user)
        # Create a personal status for testing
        self.status = Status.objects.create(
            name='View Test Status',
            creator=self.user,
            team=None,
            color='#ffffff'
        )

    def test_task_create_blocked_at_limit(self):
        """Task creation blocked when limit reached."""
        # Create 500 tasks to reach limit
        tasks = [
            Task(
                name=f'task_{i}',
                author=self.user,
                team=None,
                status=self.status
            )
            for i in range(500)
        ]
        Task.objects.bulk_create(tasks)

        # Try to create a new task
        response = self.c.post(
            reverse('tasks:task-create'),
            {
                'name': 'New Task',
                'description': 'Test',
                'status': self.status.pk,
            },
            follow=True
        )

        # Should be redirected
        self.assertEqual(response.status_code, 200)
        # Check messages for warning
        messages_list = list(get_messages(response.wsgi_request))
        warning_messages = [m for m in messages_list if m.level == 30]  # WARNING
        self.assertTrue(len(warning_messages) > 0)
        self.assertIn('500', str(warning_messages[0]))

    def test_task_create_allowed_below_limit(self):
        """Task creation allowed when below limit."""
        # Get current personal task count
        current_tasks = Task.objects.filter(
            author=self.user,
            team__isnull=True
        ).count()

        # Calculate how many more we can create (leave room for 1 more)
        tasks_to_create = min(100, 500 - current_tasks - 1)

        # Create some tasks to get close but not at limit
        if tasks_to_create > 0:
            tasks = [
                Task(
                    name=f'limit_test_task_{i}',
                    author=self.user,
                    team=None,
                    status=self.status
                )
                for i in range(tasks_to_create)
            ]
            Task.objects.bulk_create(tasks)

        # Try to create a new task - include executors as required by form
        response = self.c.post(
            reverse('tasks:task-create'),
            {
                'name': 'New Task Below Limit',
                'description': 'Test',
                'status': self.status.pk,
                'executors': [self.user.pk],
                'labels': []
            },
            follow=True
        )

        # Should not be blocked (task created)
        self.assertEqual(response.status_code, 200)
        # Task should be created
        self.assertTrue(Task.objects.filter(name='New Task Below Limit').exists())

    def test_checklist_add_blocked_at_limit(self):
        """Checklist add returns 429 when limit reached."""
        # Create a task
        task = Task.objects.create(
            name='Checklist Limit Task',
            author=self.user,
            team=None,
            status=self.status
        )

        # Create 20 checklist items
        items = [
            ChecklistItem(
                task=task,
                text=f'Item {i}',
                position=i
            )
            for i in range(20)
        ]
        ChecklistItem.objects.bulk_create(items)

        # Try to add another item
        response = self.c.post(
            reverse('tasks:checklist-add', kwargs={'uuid': task.uuid}),
            {'text': 'New Item'},
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 429)


class LimitsContextProcessorTest(TestCase):
    """Tests for limits context processor."""

    fixtures = ["tests/fixtures/test_users.json",
                "tests/fixtures/test_teams.json",
                "tests/fixtures/test_teams_memberships.json",
                "tests/fixtures/test_statuses.json"]

    def setUp(self):
        self.c = Client()

    def test_usage_in_context_for_authenticated_user(self):
        """Usage is in context for authenticated user."""
        user = User.objects.get(username='me')
        self.c.force_login(user)

        response = self.c.get(reverse('tasks:tasks-list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('usage', response.context)
        self.assertIn('show_upgrade_hint', response.context)

    def test_no_usage_for_anonymous_user(self):
        """No usage in context for anonymous user."""
        response = self.c.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        # For anonymous user, usage should not be in context
        # (context processor returns empty dict)
        self.assertNotIn('usage', response.context)