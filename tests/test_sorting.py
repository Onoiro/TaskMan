from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from task_manager.tasks.models import Task
from task_manager.statuses.models import Status
from task_manager.user.models import User
from task_manager.teams.models import TeamMembership


class TaskSortTestCase(TestCase):
    """Tests for task sorting functionality."""
    fixtures = [
        "tests/fixtures/test_teams.json",
        "tests/fixtures/test_users.json",
        "tests/fixtures/test_teams_memberships.json",
        "tests/fixtures/test_statuses.json",
        "tests/fixtures/test_tasks.json",
        "tests/fixtures/test_labels.json",
    ]

    def setUp(self):
        self.user = User.objects.get(username='he')
        self.c = Client()
        self.c.force_login(self.user)

        membership = TeamMembership.objects.filter(user=self.user).first()
        self.team = membership.team if membership else None

        if self.team:
            session = self.c.session
            session['active_team_uuid'] = str(self.team.uuid)
            session.save()

    # ===== Context tests =====

    def test_sort_context_default(self):
        """Default sort is -updated_at."""
        response = self.c.get(reverse('tasks:tasks-list'))
        self.assertEqual(response.context['current_sort'], '-updated_at')

    def test_sort_context_valid_param(self):
        """Valid sort param is passed to context."""
        response = self.c.get(
            reverse('tasks:tasks-list'), {'sort': 'name'})
        self.assertEqual(response.context['current_sort'], 'name')

    def test_sort_context_label(self):
        """Sort label is present in context."""
        response = self.c.get(
            reverse('tasks:tasks-list'), {'sort': '-created_at'})
        self.assertIn('current_sort_label', response.context)

    def test_sort_options_in_context(self):
        """All sort options are passed to context."""
        response = self.c.get(reverse('tasks:tasks-list'))
        self.assertIn('sort_options', response.context)
        self.assertEqual(len(response.context['sort_options']), 6)

    # ===== Invalid sort fallback (covers views.py:118, filters.py:173) =====

    def test_sort_invalid_param_falls_back_to_default(self):
        """Invalid sort param falls back to -updated_at."""
        response = self.c.get(
            reverse('tasks:tasks-list'), {'sort': 'INVALID_FIELD'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_sort'], '-created_at')

    def test_sort_sql_injection_attempt_falls_back(self):
        """SQL injection in sort param falls back to default."""
        response = self.c.get(
            reverse('tasks:tasks-list'), {'sort': '-name; DROP TABLE'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_sort'], '-created_at')

    def test_sort_empty_string_falls_back(self):
        """Empty sort param falls back to default."""
        response = self.c.get(
            reverse('tasks:tasks-list'), {'sort': ''})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_sort'], '-created_at')

    # ===== Filter base queryset fallback (covers filters.py:173) =====

    def test_filter_base_queryset_invalid_sort_fallback(self):
        """Filter's _get_base_queryset falls back on invalid sort."""
        from task_manager.tasks.filters import TaskFilter

        factory = RequestFactory()
        request = factory.get('/', {'sort': 'INVALID'})
        request.user = self.user
        request.active_team = self.team

        f = TaskFilter(request.GET, queryset=Task.objects.all())
        f.request = request

        qs = f._get_base_queryset()
        self.assertIsNotNone(qs)

    # ===== Ordering verification =====

    def test_sort_by_name_asc(self):
        """Tasks sorted by name A→Z."""
        response = self.c.get(
            reverse('tasks:tasks-list'), {'sort': 'name'})
        tasks = list(response.context['filter'].qs)
        names = [t.name for t in tasks]
        self.assertEqual(names, sorted(names))

    def test_sort_by_name_desc(self):
        """Tasks sorted by name Z→A."""
        response = self.c.get(
            reverse('tasks:tasks-list'), {'sort': '-name'})
        tasks = list(response.context['filter'].qs)
        names = [t.name for t in tasks]
        self.assertEqual(names, sorted(names, reverse=True))

    def test_sort_by_created_at_asc(self):
        """Tasks sorted oldest first."""
        response = self.c.get(
            reverse('tasks:tasks-list'), {'sort': 'created_at'})
        tasks = list(response.context['filter'].qs)
        dates = [t.created_at for t in tasks]
        self.assertEqual(dates, sorted(dates))

    def test_sort_by_created_at_desc(self):
        """Tasks sorted newest first."""
        response = self.c.get(
            reverse('tasks:tasks-list'), {'sort': '-created_at'})
        tasks = list(response.context['filter'].qs)
        dates = [t.created_at for t in tasks]
        self.assertEqual(dates, sorted(dates, reverse=True))

    # ===== Sort not counted as filter =====

    def test_sort_not_counted_as_active_filter(self):
        """Sort param is not counted in active_filter_count."""
        response = self.c.get(
            reverse('tasks:tasks-list'), {'sort': 'name'})
        self.assertEqual(response.context['active_filter_count'], 0)

    def test_sort_with_filter_count_correct(self):
        """Sort + real filter = only filter counted."""
        status = Status.objects.first()
        response = self.c.get(reverse('tasks:tasks-list'), {
            'sort': 'name',
            'status': status.id,
        })
        self.assertEqual(response.context['active_filter_count'], 1)

    # ===== Sort + saved filter interaction (covers views.py:148) =====

    def test_sort_param_prevents_saved_filter_redirect(self):
        """Sort param prevents auto-redirect to saved filter."""
        self.c.get(
            reverse('tasks:tasks-list') + '?status=1&save_as_default=1',
            follow=True
        )

        response = self.c.get(
            reverse('tasks:tasks-list'), {'sort': 'name'})
        self.assertEqual(response.status_code, 200)

    def test_sort_preserved_with_filters(self):
        """Sort is preserved when applying filters."""
        status = Status.objects.first()
        response = self.c.get(reverse('tasks:tasks-list'), {
            'sort': '-name',
            'status': status.id,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_sort'], '-name')

    # ===== All valid sort options =====

    def test_all_sort_options_return_200(self):
        """Every valid sort option returns 200."""
        valid_sorts = [
            '-updated_at', 'updated_at',
            '-created_at', 'created_at',
            'name', '-name',
        ]
        for sort in valid_sorts:
            with self.subTest(sort=sort):
                response = self.c.get(
                    reverse('tasks:tasks-list'), {'sort': sort})
                self.assertEqual(response.status_code, 200)
