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
