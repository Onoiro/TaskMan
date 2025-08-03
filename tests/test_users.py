from task_manager.user.models import User
from task_manager.teams.models import Team
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.messages import get_messages
from django.utils.translation import gettext as _
from django.contrib.auth.hashers import check_password


class UserTestCase(TestCase):
    fixtures = ["tests/fixtures/test_teams.json",
                "tests/fixtures/test_users.json",
                "tests/fixtures/test_statuses.json",
                "tests/fixtures/test_tasks.json",
                "tests/fixtures/test_labels.json"]

    def setUp(self):
        self.user = User.objects.get(username="he")
        self.c = Client()
        self.c.force_login(self.user)
        self.user_data = {
            'first_name': 'New',
            'last_name': 'N',
            'username': 'new',
            'password1': 222,
            'password2': 222,
            'is_team_admin': True,
            'team_name': ''
        }

    # list

    def test_user_list_response_200(self):
        response = self.c.get(reverse('user:user-list'))
        self.assertEqual(response.status_code, 200)

    def test_user_list_content(self):
        response = self.c.get(reverse('user:user-list'))
        self.assertContains(response, 'ID')
        self.assertContains(response, _('User name'))
        self.assertContains(response, _('Fullname'))
        self.assertContains(response, _('Team admin'))
        self.assertContains(response, _('Created at'))
        self.assertContains(response, _('Users'))

    # create

    def test_create_user_page_content(self):
        response = self.c.get(reverse('user:user-create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, _('First name'))
        self.assertContains(response, _('Last name'))
        self.assertContains(response, _('Username'))
        self.assertContains(response, _('Password'))
        self.assertContains(response, _('Confirm password'))
        self.assertContains(response, _('Signup'))
        self.assertRegex(
            response.content.decode('utf-8'),
            _(r'\bSign up\b'))

    def test_create_user_successfully(self):
        old_count = User.objects.count()
        response = self.c.post(reverse('user:user-create'),
                               self.user_data, follow=True)
        self.assertEqual(response.status_code, 200)
        new_count = User.objects.count()
        self.assertEqual(old_count + 1, new_count)
        user = User.objects.filter(username=self.user_data['username']).first()
        self.assertEqual(user.first_name, self.user_data['first_name'])
        self.assertEqual(user.last_name, self.user_data['last_name'])
        self.assertRedirects(response, reverse('teams:team-create'))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]), _('User created successfully'))

    def test_create_user_non_team_admin_redirect(self):
        """Тест редиректа обычного пользователя на список задач"""
        user_data = self.user_data.copy()
        user_data['is_team_admin'] = False
        
        response = self.c.post(reverse('user:user-create'), user_data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что пользователь создан
        user = User.objects.filter(username=user_data['username']).first()
        self.assertIsNotNone(user)
        self.assertFalse(user.is_team_admin)
        
        # Проверяем редирект на список задач
        self.assertRedirects(response, reverse('index'))

    def test_check_for_not_create_user_with_same_username(self):
        self.c.post(
            reverse('user:user-create'), self.user_data, follow=True)
        users_count = User.objects.count()
        response = self.c.post(
            reverse('user:user-create'), self.user_data, follow=True)
        new_users_count = User.objects.count()
        self.assertEqual(users_count, new_users_count)
        self.assertNotEqual(response.status_code, 302)
        message = _('A user with that username already exists.')
        self.assertContains(response, message)

    def test_can_not_create_user_with_empty_name(self):
        self.user_data['username'] = ' '
        response = self.c.post(reverse('user:user-create'),
                               self.user_data, follow=True)
        self.assertFalse(User.objects.filter(username=" ").exists())
        message = _('This field is required.')
        self.assertContains(response, message)

    # update

    def test_update_user_status_200_and_check_content(self):
        response = self.c.get(
            reverse('user:user-update', args=[self.user.id]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, _('First name'))
        self.assertContains(response, _('Last name'))
        self.assertContains(response, _('Username'))
        self.assertContains(response, _('Password'))
        self.assertContains(response, _('Confirm password'))
        self.assertRegex(
            response.content.decode('utf-8'), _(r'\bEdit user\b'))
        self.assertRegex(
            response.content.decode('utf-8'), _(r'\bEdit\b'))
        self.assertContains(response, self.user.first_name)
        self.assertContains(response, self.user.last_name)
        self.assertContains(response, self.user.username)
        self.assertContains(response, self.user.first_name)

    def test_update_user_successfully(self):
        response = self.c.post(
            reverse('user:user-update', args=[self.user.id]),
            self.user_data, follow=True)
        self.assertEqual(response.status_code, 200)

        self.assertRedirects(response, reverse('user:user-list'))

        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]), _('User updated successfully'))

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, self.user_data['first_name'])
        self.assertEqual(self.user.last_name, self.user_data['last_name'])
        self.assertEqual(self.user.username, self.user_data['username'])
        self.assertTrue(
            check_password(self.user_data['password1'], self.user.password))

    def test_check_can_not_update_user_if_same_user_exist(self):
        new_user_data = {
            'first_name': 'New',
            'last_name': 'N',
            'username': 'me',  # username 'me' exists in test_users.json
            'password1': 222,
            'password2': 222,
        }
        response = self.c.post(
            reverse('user:user-update', args=[self.user.id]),
            new_user_data, follow=True)
        message = _('A user with that username already exists.')
        self.assertContains(response, message)
        self.assertNotEqual(response.status_code, 302)

    def test_can_not_set_empty_name_when_update_user(self):
        new_user_data = {
            'first_name': 'New',
            'last_name': 'N',
            'username': ' ',
            'password1': 222,
            'password2': 222,
        }
        response = self.c.post(
            reverse('user:user-update', args=[self.user.id]),
            new_user_data, follow=True)
        self.assertFalse(User.objects.filter(username=" ").exists())
        message = _('This field is required.')
        self.assertContains(response, message)

    # delete

    def test_get_delete_user_response_200_and_check_content(self):
        self.c.post(reverse('user:user-create'),
                    self.user_data, follow=True)
        new_user = User.objects.get(username="new")
        self.c.force_login(new_user)
        response = self.c.get(
            reverse('user:user-delete',
                    args=[new_user.id]), follow=False)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, _('Delete user'))
        self.assertContains(response, _('Yes, delete'))
        self.assertContains(response,
                            _('Are you sure you want to delete New N?'))

    def test_delete_user_successfully(self):
        self.c.post(reverse('user:user-create'),
                    self.user_data, follow=True)
        user = User.objects.get(username="new")
        self.c.force_login(user)
        response = self.c.post(reverse('user:user-delete',
                                       args=[user.id]), follow=True)
        self.assertFalse(User.objects.filter(username="new").exists())
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('user:user-list'))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]),
                         _('User deleted successfully'))

    def test_can_not_delete_user_bound_with_task(self):
        response = self.c.get(reverse('user:user-delete',
                                      args=[self.user.id]), follow=True)
        self.assertTrue(User.objects.filter(username="he").exists())
        self.assertRedirects(response, reverse('user:user-list'))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]),
                         _('Cannot delete a user because it is in use'))

    def test_can_not_delete_user_being_team_admin(self):
        # Create new user
        self.c.post(reverse('user:user-create'),
                    self.user_data, follow=True)
        new_user = User.objects.get(username="new")

        # Create new team with new user as team admin
        team = Team.objects.create(
            name="New Test Team",
            description="Test team description",
            team_admin=new_user
        )
        self.c.force_login(new_user)

        # Try to delete new user
        response = self.c.get(reverse('user:user-delete',
                                      args=[new_user.id]), follow=True)

        # Check that new user still exist
        self.assertTrue(User.objects.filter(username="new").exists())

        # Check for redirect
        self.assertRedirects(response, reverse('user:user-list'))

        # Check for error message
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]),
                         _('Cannot delete a user because it is team admin. '
                         'Delete the team first.'))

        # Delete team after test
        team.delete()

    def test_can_join_existing_team(self):
        team = Team.objects.get(pk=1)
        new_user_data = {
            'first_name': 'Team',
            'last_name': 'Member',
            'username': 'team_member',
            'password1': '123',
            'password2': '123',
            'is_team_admin': False,
            'team_name': team.name
        }
        response = self.c.post(reverse('user:user-create'),
                               new_user_data, follow=True)
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(username='team_member')
        self.assertEqual(user.team, team)
        self.assertFalse(user.is_team_admin)
