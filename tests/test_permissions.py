from django.test import TestCase, Client
from django.urls import reverse
# from django.contrib.auth.models import User
from task_manager.user.models import User
from task_manager.teams.models import Team, TeamMembership
from django.contrib.messages import get_messages
from django.utils.translation import gettext as _


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

    def test_custom_permissions_redirect_unauthenticated_user(self):
        response = self.client.get(reverse(
            'user:user-update', args=[self.he.id]), follow=True)
        self.assertRedirects(response, reverse('login'))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]),
                         _('You are not authorized! Please login.'))

    def test_user_permissions_can_not_modifying_other_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse(
            'user:user-update', args=[self.he.id]), follow=True)
        self.assertRedirects(response, reverse('user:user-list'))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(
            str(messages[0]),
            _("You don't have permissions to modify another user."))

    def test_user_permissions_can_modify_own_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse(
            'user:user-update', args=[self.user.id]))
        self.assertEqual(response.status_code, 200)

    def test_team_admin_permissions_unauthenticated_user(self):
        response = self.client.get(reverse(
            'teams:team-update', args=[self.team1.id]), follow=True)
        self.assertRedirects(response, reverse('login'))

    def test_team_admin_permissions_non_admin_user(self):
        self.client.force_login(self.he)
        response = self.client.get(reverse(
            'teams:team-update', args=[self.team1.id]), follow=True)
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
            'teams:team-update', args=[self.team1.id]))
        self.assertEqual(response.status_code, 200)

    def test_team_admin_permissions_user_not_in_team(self):
        self.client.force_login(self.alone)
        response = self.client.get(reverse(
            'teams:team-update', args=[self.team1.id]), follow=True)
        self.assertRedirects(response, reverse('user:user-list'))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(
            str(messages[0]),
            _("You don't have permissions to modify this."
              " Only team admin can do this."))

    def test_team_membership_admin_permissions_unauthenticated_user(self):
        membership = TeamMembership.objects.get(pk=2)
        response = self.client.get(reverse(
            'teams:team-member-role-update', args=[membership.id]), follow=True)
        self.assertRedirects(response, reverse('login'))

    def test_team_membership_admin_permissions_non_admin_user(self):
        self.client.force_login(self.he)
        membership = TeamMembership.objects.get(pk=2)
        response = self.client.get(reverse(
            'teams:team-member-role-update', args=[membership.id]), follow=True)
        self.assertRedirects(response, reverse('teams:team-detail', kwargs={'pk': membership.team.pk}))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(
            str(messages[0]),
            _("You don't have permissions to manage team members."
              " Only team admin can do this."))

    def test_team_membership_admin_permissions_admin_user(self):
        self.client.force_login(self.user)
        membership = TeamMembership.objects.get(pk=2)
        response = self.client.get(reverse(
            'teams:team-member-role-update', args=[membership.id]))
        self.assertEqual(response.status_code, 200)

    def test_team_membership_admin_permissions_trying_to_change_own_role(self):
        self.client.force_login(self.user)
        membership = TeamMembership.objects.get(pk=1)
        response = self.client.get(reverse(
            'teams:team-member-role-update', args=[membership.id]), follow=True)
        self.assertRedirects(response, reverse('teams:team-detail', kwargs={'pk': membership.team.pk}))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(
            str(messages[0]),
            _("You cannot change your own role in the team."))

    def test_team_membership_admin_permissions_nonexistent_membership(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse(
            'teams:team-member-role-update', args=[999]), follow=True)
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
        response = self.client.get(reverse(
            'teams:team-member-role-update', args=[membership.id]), follow=True)
        self.assertRedirects(response, reverse('teams:team-detail', kwargs={'pk': membership.team.pk}))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(
            str(messages[0]),
            _("You don't have permissions to manage team members."
              " Only team admin can do this."))
