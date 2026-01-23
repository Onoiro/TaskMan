from datetime import date
from task_manager.tasks.models import Task
from task_manager.statuses.models import Status
from task_manager.labels.models import Label
from task_manager.user.models import User
from task_manager.teams.models import TeamMembership
from django.test import TestCase, Client
from django.urls import reverse


class TaskTestCase(TestCase):
    fixtures = ["tests/fixtures/test_teams.json",
                "tests/fixtures/test_users.json",
                "tests/fixtures/test_teams_memberships.json",
                "tests/fixtures/test_statuses.json",
                "tests/fixtures/test_tasks.json",
                "tests/fixtures/test_labels.json"
                ]

    def setUp(self):
        self.user = User.objects.get(username='he')  # id=12
        self.status = Status.objects.get(name='at work')
        self.label = Label.objects.get(name='bug')
        self.c = Client()
        self.c.force_login(self.user)

        membership = TeamMembership.objects.filter(user=self.user).first()
        self.team = membership.team if membership else None

        # set active_team_id in session if team is set
        if self.team:
            session = self.c.session
            session['active_team_id'] = self.team.id
            session.save()

        # filter tasks by status, executor, label and team
        if self.team:
            self.filtered_tasks = Task.objects.filter(
                executor=self.user,
                status=self.status,
                labels=self.label,
                team=self.team
            )
        else:
            self.filtered_tasks = Task.objects.filter(
                executor=self.user,
                status=self.status,
                labels=self.label,
                team__isnull=True
            )

        self.response = self.c.get(reverse('tasks:tasks-list'),
                                   {'executor': self.user.id,
                                    'status': self.status.id,
                                    'labels': self.label.id
                                    })

    def test_task_list_response_200(self):
        self.assertEqual(self.response.status_code, 200)

    def test_filter_tasks_by_status_executor_label(self):
        filtered_task_ids = list(
            self.filtered_tasks.values_list('id', flat=True)
        )

        self.assertIn('filter', self.response.context)

        response_task_ids = list(
            self.response.context['filter'].qs.values_list('id', flat=True)
        )

        self.assertListEqual(
            sorted(filtered_task_ids),
            sorted(response_task_ids)
        )

    def test_filter_own_tasks(self):
        user = User.objects.get(username="me")  # id=10
        self.c.logout()
        self.c.force_login(user)

        membership = TeamMembership.objects.filter(user=user).first()
        team = membership.team if membership else None

        # set active_team_id in session if team is set
        if team:
            session = self.c.session
            session['active_team_id'] = team.id
            session.save()

        # make request with self_tasks=on to filter own tasks
        response = self.c.get(reverse('tasks:tasks-list'), {'self_tasks': 'on'})

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs

        # check if all tasks are from user
        for task in filtered_tasks:
            self.assertEqual(task.author, user)

    def test_filter_by_status_only(self):
        """Test filtering by status only"""
        response = self.c.get(reverse('tasks:tasks-list'),
                              {'status': self.status.id})

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs
        for task in filtered_tasks:
            self.assertEqual(task.status, self.status)

    def test_filter_by_executor_only(self):
        """Test filtering by executor only"""
        response = self.c.get(reverse('tasks:tasks-list'),
                              {'executor': self.user.id})

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs
        for task in filtered_tasks:
            self.assertEqual(task.executor, self.user)

    def test_filter_by_label_only(self):
        """Test filtering by label only"""
        response = self.c.get(reverse('tasks:tasks-list'),
                              {'labels': self.label.id})

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs
        for task in filtered_tasks:
            self.assertIn(self.label, task.labels.all())

    def test_empty_filter(self):
        """Test that empty filter returns all available tasks"""
        response = self.c.get(reverse('tasks:tasks-list'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs

        # get all tasks available for user
        if self.team:
            expected_tasks = Task.objects.filter(team=self.team)
        else:
            expected_tasks = Task.objects.filter(
                author=self.user, team__isnull=True
            )

        self.assertEqual(filtered_tasks.count(), expected_tasks.count())

    def test_filter_without_team(self):
        """Test filter for user without team"""
        user_no_team = User.objects.create_user(
            username='no_team_user',
            password='testpass123'
        )

        status = Status.objects.create(
            name='Personal Status',
            creator=user_no_team
        )

        task = Task.objects.create(
            name='Personal Task',
            author=user_no_team,
            executor=user_no_team,
            status=status,
            team=None
        )

        self.c.logout()
        self.c.force_login(user_no_team)

        # request without filters
        response = self.c.get(reverse('tasks:tasks-list'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs

        # user with no team has to see only his task
        self.assertEqual(filtered_tasks.count(), 1)
        self.assertEqual(filtered_tasks.first(), task)

        # cleanup
        task.delete()
        status.delete()
        user_no_team.delete()

    def test_filter_by_created_after(self):
        """Test filtering by created_after date"""
        # 2024-04-05T16:09:14.936Z is the earliest task date in fixtures
        response = self.c.get(reverse('tasks:tasks-list'),
                              {'created_after': '2024-04-06'})

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs

        for task in filtered_tasks:
            self.assertGreaterEqual(task.created_at.date(), date(2024, 4, 6))

    def test_filter_by_created_before(self):
        """Test filtering by created_before date"""
        # 2024-04-05T16:09:14.936Z is the earliest task date in fixtures
        response = self.c.get(reverse('tasks:tasks-list'),
                              {'created_before': '2024-04-05'})

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs

        for task in filtered_tasks:
            self.assertLessEqual(task.created_at.date(), date(2024, 4, 5))

    def test_filter_by_date_range(self):
        """Test filtering by created_after and created_before together"""
        response = self.c.get(reverse('tasks:tasks-list'), {
            'created_after': '2024-04-05',
            'created_before': '2024-04-06'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs

        for task in filtered_tasks:
            self.assertGreaterEqual(task.created_at.date(), date(2024, 4, 5))
            self.assertLessEqual(task.created_at.date(), date(2024, 4, 6))

    def test_filter_exclude_by_status(self):
        """Test exclude mode for status filter"""
        # Get a different status to exclude
        other_status = Status.objects.exclude(pk=self.status.pk).first()
        if not other_status:
            self.skipTest("No other status available for exclude test")

        response = self.c.get(reverse('tasks:tasks-list'), {
            'status': other_status.pk,
            'status_exclude': 'on'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs

        # All tasks should NOT have the excluded status
        for task in filtered_tasks:
            self.assertNotEqual(task.status, other_status)

    def test_filter_exclude_by_executor(self):
        """Test exclude mode for executor filter"""
        # Get another user who is executor of some tasks
        other_user = User.objects.exclude(pk=self.user.pk).first()
        if not other_user:
            self.skipTest("No other user available for exclude test")

        response = self.c.get(reverse('tasks:tasks-list'), {
            'executor': other_user.pk,
            'executor_exclude': 'on'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs

        # All tasks should NOT have the excluded executor
        for task in filtered_tasks:
            self.assertNotEqual(task.executor, other_user)

    def test_filter_exclude_by_label(self):
        """Test exclude mode for label filter"""
        # Get another label to exclude
        other_label = Label.objects.exclude(pk=self.label.pk).first()
        if not other_label:
            self.skipTest("No other label available for exclude test")

        response = self.c.get(reverse('tasks:tasks-list'), {
            'labels': other_label.pk,
            'labels_exclude': 'on'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs

        # All tasks should NOT have the excluded label
        for task in filtered_tasks:
            self.assertNotIn(other_label, task.labels.all())

    def test_filter_exclude_own_tasks(self):
        """Test exclude mode for self_tasks filter"""
        response = self.c.get(reverse('tasks:tasks-list'), {
            'self_tasks': 'on',
            'self_tasks_exclude': 'on'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs

        # All tasks should NOT be authored by the current user
        for task in filtered_tasks:
            self.assertNotEqual(task.author, self.user)

    def test_filter_combined_with_exclude(self):
        """Test combining regular filter with exclude filter"""
        other_status = Status.objects.exclude(pk=self.status.pk).first()
        if not other_status:
            self.skipTest("No other status available for combined test")

        response = self.c.get(reverse('tasks:tasks-list'), {
            'status': other_status.pk,
            'status_exclude': 'on',
            'executor': self.user.id
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs

        # Tasks should have the specified executor
        for task in filtered_tasks:
            self.assertEqual(task.executor, self.user)
            # And should NOT have the excluded status
            self.assertNotEqual(task.status, other_status)

    def test_filter_exclude_invalid_value(self):
        """Test exclude filter with invalid value (should behave as include)"""
        # Using invalid exclude value should work as normal include
        response = self.c.get(reverse('tasks:tasks-list'), {
            'status': self.status.pk,
            'status_exclude': 'invalid_value'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs

        # Should include tasks with the status (not exclude)
        for task in filtered_tasks:
            self.assertEqual(task.status, self.status)

    def test_filter_date_edge_case_same_day(self):
        """Test date filter when created_after equals created_before"""
        response = self.c.get(reverse('tasks:tasks-list'), {
            'created_after': '2024-04-05',
            'created_before': '2024-04-05'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs

        # Should return tasks created on that specific day
        for task in filtered_tasks:
            self.assertEqual(task.created_at.date(), date(2024, 4, 5))

    def test_filter_no_matching_date(self):
        """Test date filter with range that matches no tasks"""
        response = self.c.get(reverse('tasks:tasks-list'), {
            'created_after': '2025-01-01',
            'created_before': '2025-12-31'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs

        # Should return empty queryset
        self.assertEqual(filtered_tasks.count(), 0)

    def test_filter_exclude_self_tasks_with_other_filters(self):
        """Test exclude self_tasks combined with other filters"""
        other_status = Status.objects.exclude(pk=self.status.pk).first()
        if not other_status:
            self.skipTest("No other status available for this test")

        response = self.c.get(reverse('tasks:tasks-list'), {
            'self_tasks': 'on',
            'self_tasks_exclude': 'on',
            'status': self.status.pk
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs

        # Tasks should NOT be authored by current user
        # And should have the specified status
        for task in filtered_tasks:
            self.assertNotEqual(task.author, self.user)
            self.assertEqual(task.status, self.status)
