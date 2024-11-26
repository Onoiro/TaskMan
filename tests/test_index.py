from django.test import TestCase
from django.urls import reverse
from django.utils.translation import gettext as _


class IndexViewTestCase(TestCase):

    def test_index_view_status_code(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)

    def test_index_view_template_used(self):
        response = self.client.get(reverse('index'))
        self.assertTemplateUsed(response, 'index.html')

    def test_index_view_content(self):
        response = self.client.get(reverse('index'))
        self.assertContains(response, _("Welcome to Task Manager!"))
        self.assertContains(response, _('Task Manager is a web application '
                                        'designed to manage tasks '
                                        'in an organization or team.<br>'
                                        'Task Manager allows users to '
                                        'register, create and effectively '
                                        'manage tasks.'))
