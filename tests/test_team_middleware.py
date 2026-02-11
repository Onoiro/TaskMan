from django.test import TestCase, RequestFactory
from unittest.mock import Mock, patch
from task_manager.middleware.team_middleware import ActiveTeamMiddleware
from task_manager.teams.models import Team


class ActiveTeamMiddlewareTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = ActiveTeamMiddleware(get_response=Mock())

    def test_anonymous_user(self):
        # test case: user is not logged in
        request = self.factory.get('/')
        request.user = Mock()
        request.user.is_authenticated = False

        self.middleware.process_request(request)

        # active_team should be none
        self.assertIsNone(request.active_team)

    def test_authenticated_no_session(self):
        # test case: user logged in but no team in session
        request = self.factory.get('/')
        request.user = Mock()
        request.user.is_authenticated = True
        request.session = {}

        self.middleware.process_request(request)

        # active_team should be none
        self.assertIsNone(request.active_team)

    @patch('task_manager.teams.models.Team.objects.get')
    def test_authenticated_valid_team(self, mock_get):
        # test case: user logged in and has valid team
        request = self.factory.get('/')
        request.user = Mock()
        request.user.is_authenticated = True
        request.session = {'active_team_id': 1}

        # mock database returning a team
        mock_team = Mock()
        mock_get.return_value = mock_team

        self.middleware.process_request(request)

        # active_team should be the mocked team
        self.assertEqual(request.active_team, mock_team)
        # verify get was called with correct args
        mock_get.assert_called_with(
            id=1,
            memberships__user=request.user
        )

    @patch('task_manager.teams.models.Team.objects.get')
    def test_authenticated_invalid_team(self, mock_get):
        # test case: team in session does not exist (triggers exception)
        request = self.factory.get('/')
        request.user = Mock()
        request.user.is_authenticated = True
        request.session = {'active_team_id': 999}

        # mock database raising DoesNotExist
        mock_get.side_effect = Team.DoesNotExist

        self.middleware.process_request(request)

        # active_team should be none
        self.assertIsNone(request.active_team)
        # verify session key was removed
        self.assertNotIn('active_team_id', request.session)
