"""
Tests for views in task_manager/views.py
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.messages import get_messages

from task_manager.user.models import User
from task_manager.tasks.models import Task
from task_manager.statuses.models import Status


class LimitsInfoViewTestCase(TestCase):
    """Tests for LimitsInfoView."""

    fixtures = [
        "tests/fixtures/test_users.json",
        "tests/fixtures/test_teams.json",
        "tests/fixtures/test_teams_memberships.json",
        "tests/fixtures/test_statuses.json",
    ]

    def setUp(self):
        self.user = User.objects.get(username='me')
        self.c = Client()
        self.c.force_login(self.user)
        # Create a personal status for task creation
        self.status = Status.objects.create(
            name='Limits Info Test Status',
            creator=self.user,
            team=None,
            color='#ffffff'
        )

    def test_limits_info_view_get_authenticated(self):
        """Test limits info page loads correctly for authenticated user."""
        response = self.c.get(reverse('limits-info'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'limits/limits_info.html')
        self.assertIn('usage', response.context)
        self.assertIn('limits', response.context)

    def test_limits_info_view_usage_percentages_calculated(self):
        """Test that usage percentages are correctly calculated."""
        # Create some tasks to have non-zero usage
        tasks = [
            Task(
                name=f'percent_test_task_{i}',
                author=self.user,
                team=None,
                status=self.status
            )
            for i in range(50)  # 50 out of 500 = 10%
        ]
        Task.objects.bulk_create(tasks)

        response = self.c.get(reverse('limits-info'))

        self.assertEqual(response.status_code, 200)
        usage = response.context['usage']

        # Check tasks percentage is calculated (50/500 = 10%)
        self.assertIn('tasks', usage)
        self.assertEqual(usage['tasks']['current'], 50)
        self.assertEqual(usage['tasks']['max'], 500)
        self.assertEqual(usage['tasks']['percent'], 10)

    def test_limits_info_view_zero_percentage(self):
        """Test that zero usage results in 0%."""
        # Ensure no personal tasks exist
        Task.objects.filter(author=self.user, team=None).delete()

        response = self.c.get(reverse('limits-info'))

        self.assertEqual(response.status_code, 200)
        usage = response.context['usage']

        # Check tasks percentage is 0 when current is 0
        self.assertEqual(usage['tasks']['current'], 0)
        self.assertEqual(usage['tasks']['percent'], 0)

    def test_limits_info_view_capped_at_100_percent(self):
        """Test that percentage is capped at 100%."""
        # Create 600 tasks (exceeding limit of 500)
        tasks = [
            Task(
                name=f'cap_test_task_{i}',
                author=self.user,
                team=None,
                status=self.status
            )
            for i in range(600)
        ]
        Task.objects.bulk_create(tasks)

        response = self.c.get(reverse('limits-info'))

        self.assertEqual(response.status_code, 200)
        usage = response.context['usage']

        # Check percentage is capped at 100
        self.assertEqual(usage['tasks']['current'], 600)
        self.assertEqual(usage['tasks']['percent'], 100)

    def test_limits_info_view_anonymous_redirects(self):
        """Test that anonymous user is redirected to login."""
        self.c.logout()

        response = self.c.get(reverse('limits-info'))

        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)


class MainViewsTestCase(TestCase):
    """Tests for main views in task_manager/views.py."""

    def setUp(self):
        self.c = Client()

    def test_trigger_error_raises_zero_division(self):
        """Test that trigger_error raises ZeroDivisionError."""
        # Test that the function itself raises the exception
        from task_manager import views
        with self.assertRaises(ZeroDivisionError):
            # Create a mock request
            from django.http import HttpRequest
            request = HttpRequest()
            views.trigger_error(request)

    def test_index_view_anonymous(self):
        """Test index page for anonymous user."""
        response = self.c.get(reverse('index'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'index.html')
        self.assertIn('taskman', response.context)

    def test_index_view_authenticated_no_redirect_flag(self):
        """Test index page for authenticated user without redirect flag."""
        user = User.objects.create_user(
            username='test_index_user',
            password='password123'
        )
        self.c.force_login(user)

        # Ensure redirect_after_login flag is NOT set
        self.c.session['redirect_after_login'] = False
        self.c.session.save()

        response = self.c.get(reverse('index'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'index.html')

    def test_index_view_authenticated_with_redirect_flag(self):
        """Test index page redirects to tasks when flag is set."""
        user = User.objects.create_user(
            username='test_redirect_user',
            password='password123'
        )
        self.c.force_login(user)

        # Set redirect_after_login flag
        session = self.c.session
        session['redirect_after_login'] = True
        session.save()

        response = self.c.get(reverse('index'))

        # Should redirect to tasks list
        self.assertEqual(response.status_code, 302)
        self.assertIn('tasks', response.url)

    def test_index_view_clears_redirect_flag(self):
        """Test that redirect flag is cleared after redirect."""
        user = User.objects.create_user(
            username='test_flag_clear_user',
            password='password123'
        )
        self.c.force_login(user)
        session = self.c.session
        session['redirect_after_login'] = True
        session.save()

        self.c.get(reverse('index'), follow=True)

        # Check flag was cleared
        self.assertFalse(self.c.session.get('redirect_after_login'))


class UserLoginLogoutViewsTestCase(TestCase):
    """Tests for UserLoginView and UserLogoutView."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='test_auth_user',
            password='password123'
        )
        self.c = Client()

    def test_user_login_view_success_sets_redirect_flag(self):
        """Test successful login sets redirect_after_login flag."""
        # Get the login page first to obtain CSRF token
        login_page = self.c.get(reverse('login'))
        csrf_token = login_page.context['csrf_token']

        response = self.c.post(
            reverse('login'),
            {
                'username': 'test_auth_user',
                'password': 'password123',
                'csrfmiddlewaretoken': csrf_token
            },
            follow=True
        )

        self.assertEqual(response.status_code, 200)
        # Check redirect flag was set
        self.assertTrue(self.c.session.get('redirect_after_login'))

        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)

    def test_user_logout_view_sets_info_message(self):
        """Test logout sets info message."""
        self.c.force_login(self.user)

        # Get CSRF token from session
        session = self.c.session
        csrf_token = session.get('csrf_token')

        response = self.c.post(
            reverse('logout'),
            {'csrfmiddlewaretoken': csrf_token} if csrf_token else {},
            follow=True
        )

        self.assertEqual(response.status_code, 200)

        # Check info message about logout
        messages = list(get_messages(response.wsgi_request))
        info_msgs = [m for m in messages if m.level == 20]  # INFO level
        self.assertGreater(len(info_msgs), 0)
        self.assertIn('logged out', str(info_msgs[0]).lower())
