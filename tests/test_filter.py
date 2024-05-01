from task_manager.tasks.models import Task
from task_manager.statuses.models import Status
from task_manager.labels.models import Label
from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse


class TaskTestCase(TestCase):
    fixtures = ["tests/fixtures/test_users.json",
                "tests/fixtures/test_statuses.json",
                "tests/fixtures/test_tasks.json",
                "tests/fixtures/test_labels.json"
                ]

    def setUp(self):
        self.user = User.objects.get(username='he')
        self.status = Status.objects.get(name='at work')
        self.label = Label.objects.get(name='feature')
        self.c = Client()
        self.c.force_login(self.user)
        self.filtered_tasks = Task.objects.filter(
            executor=self.user,
            status=self.status,
            labels=self.label
            )
        self.response = self.c.get(reverse('tasks:tasks-list'),
                                   {'executor': self.user.id,
                                    'status': self.status.id,
                                    'label': self.label.id
                                    })

    def test_task_list_response_200(self):
        self.assertEqual(self.response.status_code, 200)
    
    def test_filter_tasks_by_status_executor_label(self):
        filtered_task_ids = list(self.filtered_tasks.values_list('id', flat=True))
        response_task_ids = list(self.response.context['filter'].qs.values_list('id', flat=True))
        print(filtered_task_ids, response_task_ids)
        self.assertListEqual(filtered_task_ids, response_task_ids)
