from task_manager.tasks.models import Task
from django.contrib.auth.models import User
from task_manager.statuses.models import Status
from django.test import TestCase, Client
from django.urls import reverse


class TaskTestCase(TestCase):
    fixtures = ["tests/fixtures/test_users.json",
                "tests/fixtures/test_statuses.json",
                "tests/fixtures/test_tasks.json"]

    def setUp(self):
        super().setUp()
        self.user = User.objects.get(username='me')
        self.status = Status.objects.get(name='new')
        self.executor = User.objects.get(username='he')
        self.c = Client()
        self.c.force_login(self.user)
        self.tasks_data = {
            'name': 'new_test_task',
            'description': 'new_test_description',
            'status': self.status.id,
            'executor': self.executor.id
        }

    def test_create_task_response_200(self):
        response = self.c.post(reverse('tasks:task-create'),
                            self.tasks_data, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_created_task_add_to_db(self):
        old_count = Task.objects.count()
        self.c.post(reverse('tasks:task-create'),
                    self.tasks_data, follow=True)
        new_count = Task.objects.count()
        self.assertEqual(old_count + 1, new_count)

    def test_check_for_not_create_task_with_same_name(self):
        self.c.post(reverse('tasks:task-create'),
                    self.tasks_data, follow=True)
        tasks_count = Task.objects.count()
        self.c.post(reverse('tasks:task-create'),
                    self.tasks_data, follow=True)
        new_tasks_count = Task.objects.count()
        self.assertEqual(tasks_count, new_tasks_count)

    def test_create_task_with_correct_data(self):
        self.c.post(reverse('tasks:task-create'),
                    self.tasks_data, follow=True)
        task = Task.objects.filter(
            name=self.tasks_data['name']).first()
        self.assertEqual(task.name, self.tasks_data['name'])

    def test_update_task(self):
        task = Task.objects.get(name="first task")
        response = self.c.post(
            reverse('tasks:task-update', args=[task.id]),
            self.tasks_data,
            follow=True)
        self.assertEqual(response.status_code, 200)
        task.refresh_from_db()
        self.assertEqual(task.name, self.tasks_data['name'])

    def test_delete_task(self):
        task = Task.objects.get(name="first task")
        self.c.post(reverse('tasks:task-delete',
                            args=[task.id]), follow=True)
        self.assertFalse(Task.objects.filter(name="new").exists())
    
    def test_delete_task_can_only_author(self):
        self.c.logout()
        user = User.objects.get(username="he")
        self.c.force_login(user)
        task = Task.objects.get(name="second task")
        self.c.post(reverse('tasks:task-delete',
                            args=[task.id]), follow=True)
        self.assertTrue(Task.objects.filter(name="second task").exists())
