from task_manager.tasks.models import Task
from task_manager.user.models import User
from django.test import TestCase, Client
from django.urls import reverse
from django.utils.translation import gettext as _
from django.contrib.messages import get_messages
from django.utils.dateformat import DateFormat
from django.utils.formats import get_format


class TaskTestCase(TestCase):
    fixtures = ["tests/fixtures/test_teams.json",
                "tests/fixtures/test_users.json",
                "tests/fixtures/test_statuses.json",
                "tests/fixtures/test_tasks.json",
                "tests/fixtures/test_labels.json"]

    def setUp(self):
        self.user = User.objects.get(username='me')
        self.task = Task.objects.get(name="first task")
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

    def test_tasks_list_static_content(self):
        response = self.c.get(reverse('tasks:tasks-list'))
        # fields that are always visible
        self.assertContains(response, _('Tasks'))
        self.assertContains(response, _('Show'))
        self.assertContains(response, _('Label'))
        self.assertContains(response, _('Just my tasks'))

        # check that there are no titles for table if not full_view=1
        self.assertNotContains(response, '<th>ID</th>')
        self.assertNotContains(response, f'<th>{_("Name")}</th>')
        self.assertNotContains(response, f'<th>{_("Status")}</th>')
        self.assertNotContains(response, f'<th>{_("Author")}</th>')
        self.assertNotContains(response, f'<th>{_("Executor")}</th>')
        self.assertNotContains(response, f'<th>{_("Created at")}</th>')

    def test_tasks_list_full_view_content(self):
        response = self.c.get(reverse('tasks:tasks-list') + '?full_view=1')
        # all fields have to be visible if full_view=1
        self.assertContains(response, '<th>ID</th>')
        self.assertContains(response, f'<th>{_("Name")}</th>')
        self.assertContains(response, f'<th>{_("Status")}</th>')
        self.assertContains(response, f'<th>{_("Author")}</th>')
        self.assertContains(response, f'<th>{_("Executor")}</th>')
        self.assertContains(response, f'<th>{_("Created at")}</th>')
        self.assertContains(response, _('Label'))
        self.assertContains(response, _('Just my tasks'))
        self.assertContains(response, _('Tasks'))
        self.assertContains(response, _('Show'))

    def test_tasks_list_compact_view_content(self):
        response = self.c.get(reverse('tasks:tasks-list'))
        # check for main fields visible in compact view
        # self.assertContains(response, f'<th>{_("Name")}</th>')
        self.assertContains(response, _('Tasks'))
        self.assertContains(response, _('Show'))
        self.assertContains(response, _('Full view'))  # toggle button

        # these titles have not be visible in compact view
        self.assertNotContains(response, '<th>ID</th>')
        self.assertNotContains(response, f'<th>{_("Status")}</th>')
        self.assertNotContains(response, f'<th>{_("Author")}</th>')
        self.assertNotContains(response, f'<th>{_("Executor")}</th>')
        self.assertNotContains(response, f'<th>{_("Created at")}</th>')
        self.assertNotContains(response, _('Compact view'))

    def test_tasks_list_view_toggle_buttons(self):
        # check for right buttons in compact view
        response = self.c.get(reverse('tasks:tasks-list'))
        self.assertContains(response, _('Full view'))
        self.assertNotContains(response, _('Compact view'))

        # check for right buttons in compact full view
        response = self.c.get(reverse('tasks:tasks-list') + '?full_view=1')
        self.assertContains(response, _('Compact view'))
        self.assertNotContains(response, _('Full view'))

    def test_tasks_list_content(self):
        response = self.c.get(reverse('tasks:tasks-list'))
        team_user_ids = User.objects.filter(
            team=self.user.team).values_list('pk', flat=True)
        tasks = Task.objects.filter(author__in=team_user_ids)
        for task in tasks:
            self.assertContains(response, task.name)
        other_tasks = Task.objects.exclude(author__in=team_user_ids)
        for task in other_tasks:
            self.assertNotContains(response, task.name)

    # detail_view

    def test_task_detail_view_response_200(self):
        response = self.c.get(
            reverse('tasks:task-detail', args=[self.task.id]))
        self.assertEqual(response.status_code, 200)

    def test_task_detail_view_static_content(self):
        response = self.c.get(
            reverse('tasks:task-detail', args=[self.task.id]))
        self.assertContains(response, _("Task view"))
        self.assertContains(response, _('Status'))
        self.assertContains(response, _('Author'))
        self.assertContains(response, _('Executor'))
        self.assertContains(response, _('Created at'))
        self.assertContains(response, _("Labels"))
        self.assertContains(response, _("Edit"))
        self.assertContains(response, _("Delete"))

    def test_task_detail_view_content(self):
        response = self.c.get(
            reverse('tasks:task-detail', args=[self.task.id]))
        self.assertContains(response, self.task.name)
        self.assertContains(response, self.task.description)
        self.assertContains(
            response,
            f"{self.task.author.first_name}"
            f" {self.task.author.last_name}")
        self.assertContains(
            response,
            f"{self.task.executor.first_name}"
            f" {self.task.executor.last_name}")
        self.assertContains(response, self.task.status.name)
        formatted_date = DateFormat(
            self.task.created_at).format(get_format('DATETIME_FORMAT'))
        self.assertContains(response, formatted_date)
        labels = self.task.labels.all()
        label_names = [label.name for label in labels]
        for label_name in label_names:
            self.assertContains(response, label_name)

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

    # def test_create_task_user_without_team_auto_executor(self):
    #     # Создаем пользователя без команды
    #     user_without_team = User.objects.create_user(
    #         username='no_team_user',
    #         password='testpass123'
    #     )
    #     # Убеждаемся, что у пользователя нет команды
    #     user_without_team.team = None
    #     user_without_team.save()

    #     self.c.force_login(user_without_team)

    #     # Данные для создания задачи (без указания executor)
    #     task_data = {
    #         'name': 'task_by_user_without_team',
    #         'description': 'test description',
    #         'status': 12,  # предполагаем, что статус с id=12 доступен всем
    #     }

    #     response = self.c.post(reverse('tasks:task-create'),
    #  task_data, follow=True)

    #     # Проверяем, что задача создалась
    #     task = Task.objects.filter(name=task_data['name']).first()
    #     self.assertIsNotNone(task)

    #     # Проверяем, что автор и исполнитель - один и тот же пользователь
    #     self.assertEqual(task.author, user_without_team)
    #     self.assertEqual(task.executor, user_without_team)

    #     self.assertEqual(response.status_code, 200)
    #     self.assertRedirects(response, reverse('tasks:tasks-list'))

    #     # в форме executor field содержит текущего пользователя
    #     form = response.context['form']
    #     executor_queryset = form.fields['executor'].queryset
    #     self.assertEqual(executor_queryset.count(), 1)
    #     self.assertEqual(executor_queryset.first(), user_without_team)

    #     # Проверяем, что начальное значение установлено правильно
    #     self.assertEqual(form.fields['executor'].initial, user_without_team)

    def test_create_task_user_with_team_can_choose_executor(self):
        response = self.c.post(reverse('tasks:task-create'),
                               self.tasks_data, follow=True)

        task = Task.objects.filter(name=self.tasks_data['name']).first()
        self.assertIsNotNone(task)
        self.assertEqual(task.author, self.user)

        expected_executor = User.objects.get(pk=self.tasks_data['executor'])
        self.assertEqual(task.executor, expected_executor)

        self.assertEqual(response.status_code, 200)

    # def test_check_for_not_create_task_with_same_name(self):
    #     self.c.post(reverse('tasks:task-create'),
    #                 self.tasks_data, follow=True)
    #     tasks_count = Task.objects.count()
    #     response = self.c.post(reverse('tasks:task-create'),
    #                            self.tasks_data, follow=True)
    #     new_tasks_count = Task.objects.count()
    #     self.assertEqual(tasks_count, new_tasks_count)
    #     message = _('Task with this Name already exists.')
    #     self.assertContains(response, message)

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

    # def test_check_message_when_update_task_if_same_task_exist(self):
    #     self.tasks_data = {'name': 'first task'}
    #     task = Task.objects.get(name="second task")
    #     response = self.c.post(
    #         reverse('tasks:task-update', args=[task.id]),
    #         self.tasks_data, follow=True)
    #     message = _('Task with this Name already exists.')
    #     self.assertContains(response, message)

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
