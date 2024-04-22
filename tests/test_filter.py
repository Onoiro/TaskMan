from task_manager.tasks.models import Task
from task_manager.statuses.models import Status
from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse


class TaskTestCase(TestCase):
    fixtures = ["tests/fixtures/test_users.json",
                "tests/fixtures/test_statuses.json",
                "tests/fixtures/test_tasks.json",
                "tests/fixtures/test_labels.json"]

    def setUp(self):
        self.user = User.objects.get(username='me')
        self.c = Client()
        self.c.force_login(self.user)

    def test_task_list_response_200(self):
        response = self.c.get(reverse('tasks:tasks-list'))
        self.assertEqual(response.status_code, 200)
    
    # def test_filter_status_executor_label(self):
    #     response = self.c.get(reverse('tasks:tasks-list'),
    #                            self.tasks_data, follow=True)
    #     print(response.name)
    #     self.assertEqual(response.name, "new")
