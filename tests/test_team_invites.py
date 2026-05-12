"""Tests for team invite link functionality."""
from task_manager.user.models import User
from task_manager.teams.models import Team, TeamMembership, TeamInvite
from task_manager.teams.views import TeamJoinInviteView
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.messages import get_messages
from django.utils import timezone
from datetime import timedelta
from django.utils.translation import gettext as _
import uuid


class TeamInviteTestCase(TestCase):
    """Test cases for team invite link functionality."""

    fixtures = [
        "tests/fixtures/test_users.json",
        "tests/fixtures/test_teams.json",
        "tests/fixtures/test_teams_memberships.json",
    ]

    def setUp(self):
        """Set up test fixtures."""
        self.admin_user = User.objects.get(pk=10)  # user team admin
        self.c = Client()
        self.c.force_login(self.admin_user)
        self.team = Team.objects.get(pk=1)  # test team

        # Update UUIDs for fixtures
        team = Team.objects.filter(pk=1).first()
        if team and not hasattr(team, '_uuid_set'):
            team.uuid = uuid.UUID('550e8400-e29b-41d4-a716-446655440030')
            team.save(update_fields=['uuid'])
            team._uuid_set = True

    def _get_invite_url(self, invite_code):
        """Helper to get invite join URL."""
        return reverse('teams:team-join-invite', args=[invite_code])

    # Test invite generation

    def test_generate_invite_requires_admin(self):
        """test that non-admin cannot generate invite link."""
        # create regular user
        regular_user = User.objects.create_user(
            username='regular_invite_user',
            password='password123'
        )
        TeamMembership.objects.create(
            user=regular_user,
            team=self.team,
            role='member'
        )

        # login as regular user
        self.c.logout()
        self.c.force_login(regular_user)

        # try to generate invite
        response = self.c.post(
            reverse('teams:team-invite-generate', args=[self.team.uuid]),
            follow=True
        )

        # check error message
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertIn(
            _("You don't have permissions"),
            str(messages[0])
        )

    def test_generate_invite_creates_invite(self):
        """test that admin can generate invite link."""
        old_count = TeamInvite.objects.count()

        response = self.c.post(
            reverse('teams:team-invite-generate', args=[self.team.uuid]),
            follow=True
        )

        # check invite was created
        self.assertEqual(TeamInvite.objects.count(), old_count + 1)

        # check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertIn(
            _('Invite link generated successfully'),
            str(messages[0])
        )

    def test_generate_invite_deletes_existing_unused(self):
        """test that generating new invite deletes existing unused invite."""
        # create existing unused invite
        existing_invite = TeamInvite.objects.create(
            team=self.team,
            created_by=self.admin_user,
            expires_at=timezone.now() + timedelta(days=7)
        )

        # generate new invite
        self.c.post(
            reverse('teams:team-invite-generate', args=[self.team.uuid])
        )

        # check old invite was deleted
        self.assertFalse(
            TeamInvite.objects.filter(pk=existing_invite.pk).exists()
        )
        # check new invite exists
        self.assertEqual(TeamInvite.objects.count(), 1)

    def test_generate_invite_sets_correct_expiry(self):
        """test that invite expires in 7 days."""
        self.c.post(
            reverse('teams:team-invite-generate', args=[self.team.uuid])
        )

        invite = TeamInvite.objects.latest('created_at')
        expected_expiry = timezone.now() + timedelta(days=7)

        # check expiry is approximately 7 days from now
        diff = (invite.expires_at - expected_expiry).total_seconds()
        self.assertLess(abs(diff), 60)  # within 1 minute

    def test_generate_invite_store_url_in_session(self):
        """test that invite URL is stored in session."""
        self.c.post(
            reverse('teams:team-invite-generate', args=[self.team.uuid])
        )

        # check session contains invite URL
        self.assertIn('last_invite_url', self.c.session)
        self.assertTrue(self.c.session['last_invite_url'].startswith(
            'http://testserver'
        ))

    # Test invite validation

    def test_join_with_invalid_invite_code(self):
        """test that invalid invite code shows error."""
        # use a valid UUID format but non-existent code
        invalid_uuid = '00000000-0000-0000-0000-000000000000'
        response = self.c.get(
            self._get_invite_url(invalid_uuid)
        )

        # check redirect to user list
        self.assertRedirects(response, reverse('user:user-list'))

        # check error message
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertIn(
            _('Invalid or expired invite link'),
            str(messages[0])
        )

    def test_join_with_expired_invite(self):
        """test that expired invite shows error."""
        # create expired invite
        expired_invite = TeamInvite.objects.create(
            team=self.team,
            created_by=self.admin_user,
            expires_at=timezone.now() - timedelta(days=1)
        )

        response = self.c.get(
            self._get_invite_url(expired_invite.invite_code)
        )

        # check redirect
        self.assertRedirects(response, reverse('user:user-list'))

        # check error message
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertIn(_('Invite link has expired'), str(messages[0]))

    def test_join_with_used_invite(self):
        """test that used invite shows error."""
        # create and use invite
        invite = TeamInvite.objects.create(
            team=self.team,
            created_by=self.admin_user,
            expires_at=timezone.now() + timedelta(days=7)
        )
        invite.is_used = True
        invite.save()

        response = self.c.get(
            self._get_invite_url(invite.invite_code)
        )

        # check redirect
        self.assertRedirects(response, reverse('user:user-list'))

        # check error message
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertIn(
            _('Invite link has been used'),
            str(messages[0])
        )

    # Test authenticated user joining via invite

    def test_authenticated_user_joins_team_via_invite(self):
        """test authenticated user can join team via invite."""
        # create invite
        invite = TeamInvite.objects.create(
            team=self.team,
            created_by=self.admin_user,
            expires_at=timezone.now() + timedelta(days=7)
        )

        # create regular user
        regular_user = User.objects.create_user(
            username='invite_join_user',
            password='password123'
        )
        self.c.logout()
        self.c.force_login(regular_user)

        # join via invite
        response = self.c.get(
            self._get_invite_url(invite.invite_code),
            follow=True
        )

        # check user joined team
        self.assertTrue(
            TeamMembership.objects.filter(
                user=regular_user,
                team=self.team,
                status='active'
            ).exists()
        )

        # check invite was marked as used
        invite.refresh_from_db()
        self.assertTrue(invite.is_used)
        self.assertEqual(invite.used_by, regular_user)

        # check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertIn(
            _('You have successfully joined the team'),
            str(messages[0])
        )

    def test_authenticated_user_already_member_shows_info(self):
        """test that user already in team sees info message."""
        # create invite
        invite = TeamInvite.objects.create(
            team=self.team,
            created_by=self.admin_user,
            expires_at=timezone.now() + timedelta(days=7)
        )

        # admin user is already member
        response = self.c.get(
            self._get_invite_url(invite.invite_code),
            follow=True
        )

        # check info message
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertIn(
            _('You are already a member of this team'),
            str(messages[0])
        )

        # check invite was NOT used
        invite.refresh_from_db()
        self.assertFalse(invite.is_used)

    # Test unauthenticated user registration via invite

    def test_new_user_registers_and_joins_via_invite(self):
        """test new user can register and join team via invite."""
        # create invite
        invite = TeamInvite.objects.create(
            team=self.team,
            created_by=self.admin_user,
            expires_at=timezone.now() + timedelta(days=7)
        )

        # logout admin
        self.c.logout()

        # register and join via invite
        response = self.c.post(
            self._get_invite_url(invite.invite_code),
            {
                'username': 'new_invite_user',
                'password1': 'password1234',
                'password2': 'password1234',
            },
            follow=True
        )

        # check user was created
        self.assertTrue(User.objects.filter(
            username='new_invite_user'
        ).exists())

        # check user joined team with active status
        user = User.objects.get(username='new_invite_user')
        self.assertTrue(
            TeamMembership.objects.filter(
                user=user,
                team=self.team,
                status='active'
            ).exists()
        )

        # check invite was marked as used
        invite.refresh_from_db()
        self.assertTrue(invite.is_used)
        self.assertEqual(invite.used_by, user)

        # check user is logged in
        self.assertEqual(self.c.session.get('_auth_user_id'), str(user.pk))

        # check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertIn(
            _('Your account has been created and you have joined the team'),
            str(messages[0])
        )

    def test_register_with_weak_password_fails(self):
        """test that weak password shows validation error."""
        # create invite
        invite = TeamInvite.objects.create(
            team=self.team,
            created_by=self.admin_user,
            expires_at=timezone.now() + timedelta(days=7)
        )

        # logout admin
        self.c.logout()

        # try to register with weak password
        response = self.c.post(
            self._get_invite_url(invite.invite_code),
            {
                'username': 'weak_password_user',
                'password1': '123',
                'password2': '123',
            },
            follow=True
        )

        # check form errors (password too short)
        self.assertContains(
            response,
            _('Your password is too short')
        )

        # check invite was NOT used
        invite.refresh_from_db()
        self.assertFalse(invite.is_used)

        # check user was NOT created
        self.assertFalse(User.objects.filter(
            username='weak_password_user'
        ).exists())

    def test_register_with_mismatched_passwords_fails(self):
        """test that mismatched passwords show validation error."""
        # create invite
        invite = TeamInvite.objects.create(
            team=self.team,
            created_by=self.admin_user,
            expires_at=timezone.now() + timedelta(days=7)
        )

        # logout admin
        self.c.logout()

        # try to register with mismatched passwords
        response = self.c.post(
            self._get_invite_url(invite.invite_code),
            {
                'username': 'mismatch_password_user',
                'password1': 'password1234',
                'password2': 'differentpass',
            },
            follow=True
        )

        # check form errors
        self.assertContains(
            response,
            _('The entered passwords do not match')
        )

        # check invite was NOT used
        invite.refresh_from_db()
        self.assertFalse(invite.is_used)

    # Test team member limit

    def test_invite_join_respects_team_member_limit(self):
        """test that invite join respects FREE_PLAN max_team_members."""
        from task_manager.limits import FREE_PLAN

        # create team with max members
        full_team = Team.objects.create(
            name='Full Test Team',
            description='Team at limit',
            password='12345678'
        )
        TeamMembership.objects.create(
            user=self.admin_user,
            team=full_team,
            role='admin'
        )

        # Add members up to the limit
        for i in range(FREE_PLAN.max_team_members - 1):
            user = User.objects.create_user(
                username=f'full_team_member_{i}',
                password='password123'
            )
            TeamMembership.objects.create(
                user=user,
                team=full_team,
                role='member'
            )

        # Create invite for full team
        invite = TeamInvite.objects.create(
            team=full_team,
            created_by=self.admin_user,
            expires_at=timezone.now() + timedelta(days=7)
        )

        # Try to join via invite
        self.c.logout()
        response = self.c.post(
            self._get_invite_url(invite.invite_code),
            {
                'username': 'overflow_user',
                'password1': 'password1234',
                'password2': 'password1234',
            },
            follow=True
        )

        # check error message about limit
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertIn(
            _('Team has reached the maximum number of members'),
            str(messages[0])
        )

        # check user was NOT created
        self.assertFalse(User.objects.filter(
            username='overflow_user'
        ).exists())

        # check invite was NOT used
        invite.refresh_from_db()
        self.assertFalse(invite.is_used)

    def test_invite_prevents_join_when_team_is_full(self):
        """test that GET invite page shows error when team is full."""
        from task_manager.limits import FREE_PLAN

        # create team at limit
        full_team = Team.objects.create(
            name='Full Invite Team',
            description='Full team',
            password='12345678'
        )
        TeamMembership.objects.create(
            user=self.admin_user,
            team=full_team,
            role='admin'
        )

        # Fill to max
        for i in range(FREE_PLAN.max_team_members - 1):
            user = User.objects.create_user(
                username=f'invite_full_member_{i}',
                password='password123'
            )
            TeamMembership.objects.create(
                user=user,
                team=full_team,
                role='member'
            )

        # Create invite
        invite = TeamInvite.objects.create(
            team=full_team,
            created_by=self.admin_user,
            expires_at=timezone.now() + timedelta(days=7)
        )

        # Try to access invite page
        self.c.logout()
        response = self.c.get(
            self._get_invite_url(invite.invite_code),
            follow=True
        )

        # check error message
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertIn(
            _('Team has reached the maximum number of members'),
            str(messages[0])
        )

    # Test invite display

    def test_invite_page_shows_team_name(self):
        """test that invite page displays team name."""
        invite = TeamInvite.objects.create(
            team=self.team,
            created_by=self.admin_user,
            expires_at=timezone.now() + timedelta(days=7)
        )

        self.c.logout()
        response = self.c.get(
            self._get_invite_url(invite.invite_code)
        )

        # check team name is displayed
        self.assertContains(response, self.team.name)
        self.assertContains(response, _('Join Team via Invite'))

    def test_invite_page_shows_registration_form(self):
        """test that invite page shows registration form fields."""
        invite = TeamInvite.objects.create(
            team=self.team,
            created_by=self.admin_user,
            expires_at=timezone.now() + timedelta(days=7)
        )

        self.c.logout()
        response = self.c.get(
            self._get_invite_url(invite.invite_code)
        )

        # check form fields are present
        self.assertContains(response, 'username')
        self.assertContains(response, 'password1')
        self.assertContains(response, 'password2')
        self.assertContains(response, _('Register and Join'))

    def test_invite_page_shows_login_link(self):
        """test that invite page shows link to login."""
        invite = TeamInvite.objects.create(
            team=self.team,
            created_by=self.admin_user,
            expires_at=timezone.now() + timedelta(days=7)
        )

        self.c.logout()
        response = self.c.get(
            self._get_invite_url(invite.invite_code)
        )

        # check login link is present
        self.assertContains(response, _('Log In'))
        self.assertContains(response, reverse('login'))

    # Test edge cases

    def test_multiple_users_cannot_use_same_invite(self):
        """test that invite can only be used once."""
        # create invite
        invite = TeamInvite.objects.create(
            team=self.team,
            created_by=self.admin_user,
            expires_at=timezone.now() + timedelta(days=7)
        )

        # First user registers and joins
        self.c.logout()
        self.c.post(
            self._get_invite_url(invite.invite_code),
            {
                'username': 'first_invite_user',
                'password1': 'password1234',
                'password2': 'password1234',
            },
            follow=True
        )

        # Second user tries to use same invite
        response = self.c.post(
            self._get_invite_url(invite.invite_code),
            {
                'username': 'second_invite_user',
                'password1': 'password1234',
                'password2': 'password1234',
            },
            follow=True
        )

        # check second user was NOT created
        self.assertFalse(User.objects.filter(
            username='second_invite_user'
        ).exists())

        # check error message about used invite
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertIn(
            _('Invite link has been used'),
            str(messages[0])
        )

    def test_invite_use_count_is_incremented(self):
        """test that use_count is incremented when invite is used."""
        invite = TeamInvite.objects.create(
            team=self.team,
            created_by=self.admin_user,
            expires_at=timezone.now() + timedelta(days=7),
            max_uses=1
        )

        self.c.logout()
        self.c.post(
            self._get_invite_url(invite.invite_code),
            {
                'username': 'count_user',
                'password1': 'password1234',
                'password2': 'password1234',
            },
            follow=True
        )

        invite.refresh_from_db()
        self.assertEqual(invite.use_count, 1)

    def test_team_get_admins_method(self):
        """test Team.get_admins() returns correct admins."""
        # Create another admin for the team
        another_admin = User.objects.create_user(
            username='another_admin',
            password='password123'
        )
        TeamMembership.objects.create(
            user=another_admin,
            team=self.team,
            role='admin'
        )

        # Test get_admins method
        admins = self.team.get_admins()
        self.assertEqual(admins.count(), 2)
        self.assertIn(self.admin_user, admins)
        self.assertIn(another_admin, admins)

    def test_team_is_member_method(self):
        """test Team.is_member() returns correct result."""
        # Create a regular member
        member_user = User.objects.create_user(
            username='test_member',
            password='password123'
        )
        TeamMembership.objects.create(
            user=member_user,
            team=self.team,
            role='member'
        )

        # Test is_member for member
        self.assertTrue(self.team.is_member(member_user))

        # Test is_member for non-member
        non_member = User.objects.create_user(
            username='non_member_user',
            password='password123'
        )
        self.assertFalse(self.team.is_member(non_member))

    def test_teammembership_str_method(self):
        """test TeamMembership.__str__ returns expected format."""
        membership = TeamMembership.objects.get(
            user=self.admin_user,
            team=self.team
        )

        expected_str = f"{self.admin_user.username} - {self.team.name} (admin)"
        self.assertEqual(str(membership), expected_str)

    def test_teaminvite_str_method(self):
        """test TeamInvite.__str__ returns expected format."""
        invite = TeamInvite.objects.create(
            team=self.team,
            created_by=self.admin_user,
            expires_at=timezone.now() + timedelta(days=7)
        )

        # Test active invite string
        invite_str = str(invite)
        self.assertIn(self.team.name, invite_str)
        self.assertIn(self.admin_user.username, invite_str)
        self.assertIn(_('Active'), invite_str)

        # Test used invite string
        invite.is_used = True
        invite.save()
        invite_str = str(invite)
        self.assertIn(_('Used'), invite_str)

    def test_get_invite_without_validation_returns_none(self):
        """test _get_invite_without_validation returns None for invalid code."""
        view = TeamJoinInviteView()

        # Test with invalid UUID
        invalid_uuid = uuid.uuid4()
        result = view._get_invite_without_validation(invalid_uuid)

        self.assertIsNone(result)

    def test_get_valid_invite_handles_nonexistent_invite(self):
        """test _get_valid_invite handles non-existent invite."""
        # Create non-existent UUID
        non_existent_uuid = uuid.uuid4()

        # Use client to test the view which handles messages properly
        self.c.logout()
        response = self.c.get(
            self._get_invite_url(non_existent_uuid),
            follow=True
        )

        # Check redirect to user list
        self.assertRedirects(response, reverse('user:user-list'))

        # Check error message
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertIn(
            _('Invalid or expired invite link'),
            str(messages[0])
        )

    def test_join_team_marks_invite_as_used(self):
        """test _join_team marks invite as used correctly."""
        # Create invite
        invite = TeamInvite.objects.create(
            team=self.team,
            created_by=self.admin_user,
            expires_at=timezone.now() + timedelta(days=7)
        )

        # Create test user
        test_user = User.objects.create_user(
            username='join_test_user',
            password='password123'
        )

        # Login as test user
        self.c.logout()
        self.c.force_login(test_user)

        # Join via invite
        response = self.c.get(
            self._get_invite_url(invite.invite_code),
            follow=True
        )

        # Check invite was marked as used
        invite.refresh_from_db()
        self.assertTrue(invite.is_used)
        self.assertEqual(invite.used_by, test_user)
        self.assertIsNotNone(invite.used_at)
        self.assertEqual(invite.use_count, 1)

        # Check redirect to tasks list
        self.assertRedirects(response, reverse('tasks:tasks-list'))

        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertIn(
            _('You have successfully joined the team'),
            str(messages[0])
        )

    def test_team_detail_context_includes_usage(self):
        """test TeamDetailView context includes team_usage."""
        # Get actual active member count from database
        active_count = TeamMembership.objects.filter(
            team=self.team,
            status='active',
            user__is_deleted=False
        ).count()

        response = self.c.get(
            reverse('teams:team-detail', args=[self.team.uuid])
        )

        # Check context includes team_usage
        self.assertIn('team_usage', response.context)
        self.assertIn('active_member_count', response.context)
        self.assertEqual(
            response.context['active_member_count'],
            active_count
        )

        # Check team_usage has expected keys
        team_usage = response.context['team_usage']
        self.assertIn('members', team_usage)
        self.assertIn('tasks', team_usage)
        self.assertIn('statuses', team_usage)
        self.assertIn('labels', team_usage)
        self.assertIn('notes', team_usage)
