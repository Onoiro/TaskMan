from django.test import TestCase, Client
from django.urls import reverse
# from django.contrib.auth.models import User
from task_manager.user.models import User
from task_manager.teams.models import Team, TeamMembership
from django.contrib.messages import get_messages
from django.utils.translation import gettext as _
import uuid


class PermissionsTestCase(TestCase):
    fixtures = ["tests/fixtures/test_teams.json",
                "tests/fixtures/test_users.json",
                "tests/fixtures/test_tasks.json",
                "tests/fixtures/test_statuses.json",
                "tests/fixtures/test_labels.json",
                "tests/fixtures/test_teams_memberships.json"]

    def setUp(self):
        self.client = Client()
        self.user = User.objects.get(username='me')
        self.he = User.objects.get(username='he')
        self.alone = User.objects.get(username='alone')
        self.team1 = Team.objects.get(pk=1)
        self.team2 = Team.objects.get(pk=2)

        # Update UUIDs for fixtures that were loaded without them
        self._update_fixture_uuids()

    def _update_fixture_uuids(self):
        """Update UUIDs for fixture-loaded objects"""
        # Update teams
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

        # Update memberships
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

    def test_custom_permissions_redirect_unauthenticated_user(self):
        response = self.client.get(reverse(
            'user:user-update', args=[self.he.username]), follow=True)
        self.assertRedirects(response, reverse('login'))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]),
                         _('You are not authorized! Please login.'))

    def test_user_permissions_can_not_modifying_other_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse(
            'user:user-update', args=[self.he.username]), follow=True)
        self.assertRedirects(response, reverse('user:user-list'))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(
            str(messages[0]),
            _("You don't have permissions to modify another user."))

    def test_user_permissions_can_modify_own_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse(
            'user:user-update', args=[self.user.username]))
        self.assertEqual(response.status_code, 200)

    def test_team_admin_permissions_unauthenticated_user(self):
        response = self.client.get(reverse(
            'teams:team-update', args=[self.team1.uuid]), follow=True)
        self.assertRedirects(response, reverse('login'))

    def test_team_admin_permissions_non_admin_user(self):
        self.client.force_login(self.he)
        response = self.client.get(reverse(
            'teams:team-update', args=[self.team1.uuid]), follow=True)
        self.assertRedirects(response, reverse('user:user-list'))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(
            str(messages[0]),
            _("You don't have permissions to modify this."
              " Only team admin can do this."))

    def test_team_admin_permissions_admin_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse(
            'teams:team-update', args=[self.team1.uuid]))
        self.assertEqual(response.status_code, 200)

    def test_team_admin_permissions_user_not_in_team(self):
        self.client.force_login(self.alone)
        response = self.client.get(reverse(
            'teams:team-update', args=[self.team1.uuid]), follow=True)
        self.assertRedirects(response, reverse('user:user-list'))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(
            str(messages[0]),
            _("You don't have permissions to modify this."
              " Only team admin can do this."))

    def test_team_membership_admin_permissions_unauthenticated_user(self):
        membership = TeamMembership.objects.get(pk=2)
        url = reverse('teams:team-member-role-update',
                      args=[membership.uuid])
        response = self.client.get(url, follow=True)
        self.assertRedirects(response, reverse('login'))

    def test_team_membership_admin_permissions_non_admin_user(self):
        self.client.force_login(self.he)
        membership = TeamMembership.objects.get(pk=2)
        url = reverse('teams:team-member-role-update',
                      args=[membership.uuid])
        response = self.client.get(url, follow=True)
        self.assertRedirects(response, reverse(
            'teams:team-detail', kwargs={'uuid': membership.team.uuid}))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(
            str(messages[0]),
            _("You don't have permissions to manage team members."
              " Only team admin can do this."))

    def test_team_membership_admin_permissions_admin_user(self):
        self.client.force_login(self.user)
        membership = TeamMembership.objects.get(pk=2)
        url = reverse('teams:team-member-role-update',
                      args=[membership.uuid])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_team_membership_admin_permissions_trying_to_change_own_role(self):
        self.client.force_login(self.user)
        membership = TeamMembership.objects.get(pk=1)
        url = reverse('teams:team-member-role-update',
                      args=[membership.uuid])
        response = self.client.get(url, follow=True)
        self.assertRedirects(response, reverse(
            'teams:team-detail', kwargs={'uuid': membership.team.uuid}))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(
            str(messages[0]),
            _("You cannot change your own role in the team."))

    def test_team_membership_admin_permissions_nonexistent_membership(self):
        self.client.force_login(self.user)
        fake_uuid = "550e8400-e29b-41d4-a716-446655449999"
        url = reverse('teams:team-member-role-update',
                      args=[fake_uuid])
        response = self.client.get(url, follow=True)
        self.assertRedirects(response, reverse('user:user-list'))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(
            str(messages[0]),
            _("Team membership not found."))

    def test_team_membership_admin_permissions_admin_from_different_team(self):
        self.client.force_login(self.user)
        membership = TeamMembership.objects.get(pk=2)
        self.user.team_memberships.filter(team=membership.team).delete()
        url = reverse('teams:team-member-role-update',
                      args=[membership.uuid])
        response = self.client.get(url, follow=True)
        self.assertRedirects(response, reverse(
            'teams:team-detail', kwargs={'uuid': membership.team.uuid}))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(
            str(messages[0]),
            _("You don't have permissions to manage team members."
              " Only team admin can do this."))
