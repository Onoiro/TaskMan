from django.test import TestCase
from django.urls import reverse
from django.utils.translation import gettext as _
from django.contrib.auth import get_user_model

User = get_user_model()


class IndexViewTestCase(TestCase):

    def setUp(self):
        # Create test user for authentication tests
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_index_view_status_code_for_anonymous(self):
        # Anonymous user should see index page
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)

    def test_index_view_template_used_for_anonymous(self):
        # Anonymous user should see index.html template
        response = self.client.get(reverse('index'))
        self.assertTemplateUsed(response, 'index.html')

    def test_index_view_content_for_anonymous(self):
        # Anonymous user should see TaskMan branding
        response = self.client.get(reverse('index'))
        self.assertContains(response, _("TaskMan"))

    def test_index_redirects_to_tasks_after_login(self):
        # After login, first visit to index should redirect to tasks list
        # We need to simulate actual login through the login view
        response = self.client.post(
            reverse('login'),
            {'username': 'testuser', 'password': 'testpass123'}
        )
        # After login, get index page - should redirect to tasks
        response = self.client.get(reverse('index'))
        self.assertRedirects(response, reverse('tasks:tasks-list'))

    def test_index_always_redirects_authenticated_to_tasks(self):
        # Authenticated user is always redirected to tasks list,
        # not only on the first visit after login
        self.client.force_login(self.user)
        for __ in range(2):
            response = self.client.get(reverse('index'))
            self.assertRedirects(response, reverse('tasks:tasks-list'))

    def test_index_logo_link_shows_landing_for_authenticated(self):
        # The logo points to /?home=1 so that logged-in users
        # can still reach the landing page explicitly
        self.client.force_login(self.user)
        response = self.client.get(reverse('index'), {'home': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'index.html')
