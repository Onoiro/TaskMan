from task_manager.tasks.models import Task
from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse
from django.utils.translation import gettext as _
from django.contrib.messages import get_messages


class TaskTestCase(TestCase):
    fixtures = ["tests/fixtures/test_users.json",
                "tests/fixtures/test_statuses.json",
                "tests/fixtures/test_tasks.json",
                "tests/fixtures/test_labels.json"]

    def setUp(self):
        self.user = User.objects.get(username='me')
        self.c = Client()
        self.c.force_login(self.user)
        self.tasks_data = {
            'name': 'new_test_task',
            'description': 'new_test_description',
            'status': 12,
            'executor': 12,
            'label': 1
        }

    # list

    def test_tasks_list_response_200(self):
        response = self.c.get(reverse('tasks:tasks-list'))
        self.assertEqual(response.status_code, 200)

    def test_tasks_list_content(self):
        response = self.c.get(reverse('tasks:tasks-list'))
        self.assertContains(response, 'ID')
        self.assertContains(response, _('Name'))
        self.assertContains(response, _('Status'))
        self.assertContains(response, _('Author'))
        self.assertContains(response, _('Executor'))
        self.assertContains(response, _('Created at'))
        self.assertContains(response, _('Label'))
        self.assertContains(response, _('Just my tasks'))
        self.assertContains(response, _('Tasks'))
        self.assertContains(response, _('Show'))

    # create

    def test_create_task_response_200_and_check_content(self):
        response = self.c.get(reverse('tasks:task-create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, _('Name'))
        self.assertContains(response, _('Description'))
        self.assertContains(response, _('Status'))
        self.assertContains(response, _('Executor'))
        self.assertContains(response, _('Label'))
        self.assertContains(response, _('Create'))
        self.assertRegex(
            response.content.decode('utf-8'),
            _(r'\bCreate task\b')
        )

    def test_create_task_response_200(self):
        response = self.c.post(reverse('tasks:task-create'),
                               self.tasks_data, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_created_task_add_to_db(self):
        old_count = Task.objects.count()
        response = self.c.post(reverse('tasks:task-create'),
                               self.tasks_data, follow=True)
        new_count = Task.objects.count()
        self.assertEqual(old_count + 1, new_count)
        self.assertEqual(response.status_code, 200)

    def test_create_task_successfully(self):
        response = self.c.post(reverse('tasks:task-create'),
                               self.tasks_data, follow=True)
        task = Task.objects.filter(
            name=self.tasks_data['name']).first()
        self.assertEqual(task.name, self.tasks_data['name'])
        self.assertRedirects(response, reverse('tasks:tasks-list'))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]), _('Task created successfully'))

    def test_check_for_not_create_task_with_same_name(self):
        self.c.post(reverse('tasks:task-create'),
                    self.tasks_data, follow=True)
        tasks_count = Task.objects.count()
        response = self.c.post(reverse('tasks:task-create'),
                               self.tasks_data, follow=True)
        new_tasks_count = Task.objects.count()
        self.assertEqual(tasks_count, new_tasks_count)
        message = _('Task with this Name already exists.')
        self.assertContains(response, message)

    # update

    def test_update_task_response_200(self):
        task = Task.objects.get(name="first task")
        response = self.c.post(
            reverse('tasks:task-update', args=[task.id]),
            self.tasks_data, follow=True
        )
        self.assertEqual(response.status_code, 200)

    def test_update_task_content(self):
        task = Task.objects.get(name="first task")
        response = self.c.get(
            reverse('tasks:task-update', args=[task.id]),
            self.tasks_data, follow=True
        )
        self.assertContains(response, _('Name'))
        self.assertContains(response, _('Description'))
        self.assertContains(response, _('Status'))
        self.assertContains(response, _('Executor'))
        self.assertContains(response, _('Labels'))
        self.assertContains(response, _('Edit'))
        self.assertRegex(
            response.content.decode('utf-8'),
            _(r'\bEdit task\b')
        )

    def test_update_task_with_correct_data(self):
        task = Task.objects.get(name="first task")
        self.c.post(
            reverse('tasks:task-update', args=[task.id]),
            self.tasks_data, follow=True
        )
        task.refresh_from_db()
        self.assertEqual(task.name, self.tasks_data['name'])

    def test_check_message_when_update_task_if_same_task_exist(self):
        self.tasks_data = {'name': 'first task'}
        task = Task.objects.get(name="second task")
        response = self.c.post(
            reverse('tasks:task-update', args=[task.id]),
            self.tasks_data, follow=True)
        message = _('Task with this Name already exists.')
        self.assertContains(response, message)

    # delete

    def test_delete_task_response_200(self):
        task = Task.objects.get(name="first task")
        response = self.c.get(reverse('tasks:task-delete',
                              args=[task.id]), follow=True)
        self.assertEqual(response.status_code, 200)

    def test_delete_task_content(self):
        task = Task.objects.get(name="first task")
        response = self.c.get(reverse('tasks:task-delete',
                              args=[task.id]), follow=True)
        self.assertContains(
            response, _('Are you sure you want to delete first task?')
        )
        self.assertContains(response, _('Delete task'))
        self.assertContains(response, _('Yes, delete'))

    def test_delete_task(self):
        task = Task.objects.get(name="first task")
        self.c.post(reverse('tasks:task-delete',
                            args=[task.id]), follow=True)
        self.assertFalse(Task.objects.filter(name="first task").exists())

    def test_delete_task_check_success_message(self):
        task = Task.objects.get(name="first task")
        response = self.c.post(reverse('tasks:task-delete',
                               args=[task.id]), follow=True)
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]), _('Task deleted successfully'))

    def test_success_redirect_when_delete_task(self):
        task = Task.objects.get(name="first task")
        response = self.c.post(reverse('tasks:task-delete',
                               args=[task.id]), follow=True)
        self.assertRedirects(response, reverse('tasks:tasks-list'))

    def test_delete_task_can_only_author(self):
        self.c.logout()
        user = User.objects.get(username="he")
        self.c.force_login(user)
        task = Task.objects.get(name="second task")
        self.c.post(reverse('tasks:task-delete',
                            args=[task.id]), follow=True)
        self.assertTrue(Task.objects.filter(name="second task").exists())

    def test_check_message_when_delete_user_is_not_author_of_task(self):
        self.c.logout()
        user = User.objects.get(username="he")
        self.c.force_login(user)
        task = Task.objects.get(name="second task")
        response = self.c.post(reverse('tasks:task-delete',
                                       args=[task.id]), follow=True)
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(
            str(messages[0]),
            _('Task can only be deleted by its author.')
        )

    def test_no_redirect_when_not_delete_task(self):
        self.c.logout()
        user = User.objects.get(username="he")
        self.c.force_login(user)
        task = Task.objects.get(name="second task")
        response = self.c.post(reverse('tasks:task-delete',
                                       args=[task.id]), follow=True)
        self.assertNotEqual(response.status_code, 302)
