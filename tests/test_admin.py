from django.test import TestCase
from django.contrib.admin.sites import AdminSite
from django.urls import reverse
from task_manager.user.admin import UserAdmin
from task_manager.user.models import User
from task_manager.teams.models import Team, TeamMembership


class UserAdminTest(TestCase):
    def setUp(self):
        # create AdminSite object and UserAdmin object for testing
        self.site = AdminSite()
        self.user_admin = UserAdmin(User, self.site)

        # create one test user
        self.user = User.objects.create_user(
            username='test_admin_user',
            password='123'
        )

        # create two teams with password
        self.team1 = Team.objects.create(
            name='Alpha Team',
            password='123'
        )
        self.team2 = Team.objects.create(
            name='Beta Team',
            password='123'
        )

    def test_get_teams_empty(self):
        """ Test: when user has no teams, show "No teams" text """
        # delete all user team connections
        TeamMembership.objects.filter(user=self.user).delete()

        # call the admin method
        result = self.user_admin.get_teams(self.user)
        # check result is exactly "No teams"
        self.assertEqual(result, "No teams")

    def test_get_teams_formatting(self):
        """ Test: check that teams and roles are shown in correct format """
        # add user to team1 as admin
        TeamMembership.objects.create(
            user=self.user,
            team=self.team1,
            role='admin'
        )
        # add user to team2 as member
        TeamMembership.objects.create(
            user=self.user,
            team=self.team2,
            role='member'
        )

        # call the admin method
        result = self.user_admin.get_teams(self.user)

        # check result has correct format
        # example: "Alpha Team (admin), Beta Team"
        self.assertIn("Alpha Team (admin)", result)
        self.assertIn("Beta Team", result)
        # check that there is comma and space between teams
        self.assertIn(", ", result)

    def test_admin_user_page_status_200(self):
        """ Test: check that admin user list page opens correctly """
        # create superuser for admin access
        superuser = User.objects.create_superuser(
            'superuser', 'admin@test.com', 'password'
        )
        # login as superuser
        self.client.force_login(superuser)

        # get the URL of user list page in admin
        url = reverse('admin:user_user_changelist')

        # open the page
        response = self.client.get(url)
        # check page status is 200 (success)
        self.assertEqual(response.status_code, 200)

        # check that "Teams" column title is on the page
        # this column is defined in admin.py with:
        # get_teams.short_description = 'Teams'
        self.assertContains(response, "Teams")
