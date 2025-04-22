from task_manager.tasks.models import Task
from task_manager.statuses.models import Status
from task_manager.labels.models import Label
# from django.contrib.auth.models import User
from task_manager.user.models import User
from django.test import TestCase, Client
from task_manager.tasks.filters import TaskFilter
from django.urls import reverse


class TaskTestCase(TestCase):
    fixtures = ["tests/fixtures/test_teams.json",
                "tests/fixtures/test_users.json",
                "tests/fixtures/test_statuses.json",
                "tests/fixtures/test_tasks.json",
                "tests/fixtures/test_labels.json"
                ]

    def setUp(self):
        self.user = User.objects.get(username='he')
        self.status = Status.objects.get(name='at work')
        self.label = Label.objects.get(name='bug')
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
        filtered_task_ids = list(
            self.filtered_tasks.values_list('id', flat=True))
        response_task_ids = list(
            self.response.context['filter'].qs.values_list('id', flat=True))
        self.assertListEqual(filtered_task_ids, response_task_ids)

    def test_filter_own_tasks(self):
        filter_data = {'self_tasks': 'on'}
        self.c.logout()
        user = User.objects.get(username="me")
        self.c.force_login(user)
        filter_set = TaskFilter(
            filter_data,
            queryset=Task.objects.all(),
            request=self.c.request().wsgi_request
            # Использовал здесь ответ ChatGPT,
            # т.к. request=self.c.request давал ошибку:
            # File "/home/abo/python-project-52/task_manager/tasks/filters.py",
            # line 44, in filter_own_tasks
            #     return queryset.filter(author=self.request.user)
            # AttributeError: 'function' object has no attribute 'user'
            # Вот объяснение ChatGPT:
            # Метод wsgi_request преобразует объект запроса,
            # связанный с тестовым клиентом, в объект,
            # содержащий полезные атрибуты пользователя, такие как user,
            # которые могут использоваться для фильтрации данных.
            # Поэтому использование self.c.request().wsgi_request
            # обеспечивает корректную передачу объекта запроса пользователя
            # в фильтр и позволяет ему правильно применять фильтрацию
            # на основе данных пользователя.
        )
        filtered_tasks = filter_set.qs
        for task in filtered_tasks:
            self.assertEqual(task.author, user)
