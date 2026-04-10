"""Tests for context processors."""

from unittest.mock import MagicMock, patch

from django.test import TestCase, RequestFactory

from task_manager.context_processors import (
    team_context,
    static_version,
    limits_context,
)
from task_manager.teams.models import Team, TeamMembership
from task_manager.limit_service import LimitService
from task_manager.user.models import User


class TeamContextProcessorTestCase(TestCase):
    """Tests for team_context processor."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_team_context_unauthenticated_user(self):
        """Test team context for unauthenticated user."""
        request = self.factory.get('/')
        request.user = MagicMock()
        request.user.is_authenticated = False

        context = team_context(request)

        self.assertIn('VERSION', context)
        self.assertNotIn('user_teams', context)
        self.assertNotIn('active_team', context)
        self.assertNotIn('is_team_mode', context)

    def test_team_context_authenticated_user(self):
        """Test team context for authenticated user."""
        request = self.factory.get('/')
        request.user = self.user
        request.active_team = None

        context = team_context(request)

        self.assertIn('VERSION', context)
        self.assertIn('user_teams', context)
        self.assertIn('active_team', context)
        self.assertIn('is_team_mode', context)
        self.assertEqual(context['active_team'], None)
        self.assertFalse(context['is_team_mode'])

    def test_team_context_with_active_team(self):
        """Test team context when user has active team."""
        team = Team.objects.create(name='Test Team', password='testpass')
        TeamMembership.objects.create(
            user=self.user,
            team=team,
            status='active',
            role='admin'
        )

        request = self.factory.get('/')
        request.user = self.user
        request.active_team = team

        context = team_context(request)

        self.assertIn('VERSION', context)
        self.assertIn('user_teams', context)
        self.assertEqual(context['active_team'], team)
        self.assertTrue(context['is_team_mode'])


class StaticVersionProcessorTestCase(TestCase):
    """Tests for static_version processor."""

    @patch('task_manager.context_processors.settings')
    @patch('task_manager.context_processors.os.path')
    @patch('task_manager.context_processors.os')
    def test_static_version_when_manifest_exists(
        self, mock_os, mock_path, mock_settings
    ):
        """Test static version when manifest exists (production)."""
        mock_settings.STATIC_ROOT = '/tmp/static'
        mock_path.join.return_value = '/tmp/static/staticfiles.json'
        mock_os.path.exists.return_value = True
        mock_os.path.getmtime.return_value = 1234567890.0

        result = static_version(MagicMock())

        self.assertIn('STATIC_VERSION', result)
        self.assertNotEqual(result['STATIC_VERSION'], 'dev')
        # Версия должна быть хэшем от времени модификации
        self.assertEqual(len(result['STATIC_VERSION']), 8)

    def test_static_version_when_manifest_does_not_exist(self):
        """Test static version when manifest does not exist."""
        with patch('task_manager.context_processors.settings') as mock_settings:
            mock_settings.STATIC_ROOT = '/tmp/nonexistent'

            with patch(
                'task_manager.context_processors.os.path'
            ) as mock_path:
                mock_path.join.return_value = (
                    '/tmp/nonexistent/staticfiles.json'
                )

                with patch('task_manager.context_processors.os') as mock_os:
                    mock_os.path.exists.return_value = False
                    mock_os.path.getmtime.side_effect = OSError(
                        'File not found'
                    )

                    result = static_version(MagicMock())

        self.assertIn('STATIC_VERSION', result)
        self.assertEqual(result['STATIC_VERSION'], 'dev')


class LimitsContextProcessorTestCase(TestCase):
    """Tests for limits_context processor."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_limits_context_unauthenticated(self):
        """Test limits context for unauthenticated user."""
        request = self.factory.get('/')
        request.user = MagicMock()
        request.user.is_authenticated = False

        context = limits_context(request)

        self.assertEqual(context, {})

    def test_limits_context_authenticated(self):
        """Test limits context for authenticated user."""
        request = self.factory.get('/')
        request.user = self.user

        with patch.object(
            LimitService,
            'get_usage_summary',
            return_value={
                'teams': {'current': 1, 'max': 10},
                'tasks': {'current': 5, 'max': 100},
            }
        ):
            context = limits_context(request)

        self.assertIn('usage', context)
        self.assertIn('show_upgrade_hint', context)
        self.assertIn('free_plan_limits', context)
        self.assertEqual(context['usage']['teams']['percent'], 10)
        self.assertEqual(context['usage']['tasks']['percent'], 5)

    def test_limits_context_exception(self):
        """Test limits context handles exceptions gracefully."""
        request = self.factory.get('/')
        request.user = self.user

        with patch.object(
            LimitService,
            'get_usage_summary',
            side_effect=Exception('Service error')
        ):
            context = limits_context(request)

        self.assertEqual(context, {})

    def test_limits_context_shows_upgrade_hint_at_80_percent(self):
        """Test upgrade hint is shown when usage >= 80%."""
        request = self.factory.get('/')
        request.user = self.user

        with patch.object(
            LimitService,
            'get_usage_summary',
            return_value={
                'teams': {'current': 8, 'max': 10},
                'tasks': {'current': 5, 'max': 100},
            }
        ):
            context = limits_context(request)

        self.assertTrue(context['show_upgrade_hint'])
        self.assertEqual(context['usage']['teams']['percent'], 80)

    def test_limits_context_no_upgrade_hint_below_80_percent(self):
        """Test no upgrade hint when usage < 80%."""
        request = self.factory.get('/')
        request.user = self.user

        with patch.object(
            LimitService,
            'get_usage_summary',
            return_value={
                'teams': {'current': 7, 'max': 10},
                'tasks': {'current': 5, 'max': 100},
            }
        ):
            context = limits_context(request)

        self.assertFalse(context['show_upgrade_hint'])

    def test_limits_context_handles_zero_max(self):
        """Test limits context handles zero maximum (division by zero)."""
        request = self.factory.get('/')
        request.user = self.user

        with patch.object(
            LimitService,
            'get_usage_summary',
            return_value={
                'teams': {'current': 1, 'max': 0},
                'tasks': {'current': 5, 'max': 100},
            }
        ):
            context = limits_context(request)

        self.assertIn('usage', context)
        # Когда max=0, percent должен быть 0
        self.assertEqual(context['usage']['teams']['percent'], 0)
        self.assertEqual(context['usage']['tasks']['percent'], 5)
