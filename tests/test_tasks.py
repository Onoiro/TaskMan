from task_manager.tasks.models import Task
from task_manager.user.models import User
from task_manager.teams.models import TeamMembership
from task_manager.statuses.models import Status
from task_manager.labels.models import Label
from django.test import TestCase, Client
from django.urls import reverse
from django.utils.translation import gettext as _
from django.contrib.messages import get_messages
from django.utils.dateformat import DateFormat
from django.utils.formats import get_format


class TaskTestCase(TestCase):
    fixtures = ["tests/fixtures/test_users.json",
                "tests/fixtures/test_teams.json",
                "tests/fixtures/test_teams_memberships.json",
                "tests/fixtures/test_statuses.json",
                "tests/fixtures/test_tasks.json",
                "tests/fixtures/test_labels.json"]

    def setUp(self):
        self.user = User.objects.get(username='me')
        self.task = Task.objects.get(name="first task")
        self.c = Client()
        self.c.force_login(self.user)

        membership = TeamMembership.objects.filter(user=self.user).first()
        self.team = membership.team if membership else None

        # set active_team to session if user has team in
        if self.team:
            session = self.c.session
            session['active_team_id'] = self.team.id
            session.save()

        # get available for user statuses and labels
        if self.team:
            # team mode
            available_status = Status.objects.filter(team=self.team).first()
            available_label = Label.objects.filter(team=self.team).first()
            available_executor = User.objects.filter(
                team_memberships__team=self.team
            ).exclude(pk=self.user.pk).first() or self.user
        else:
            # individual mode
            available_status = Status.objects.filter(
                creator=self.user,
                team__isnull=True
            ).first()
            available_label = Label.objects.filter(
                creator=self.user,
                team__isnull=True
            ).first()
            available_executor = self.user

        # if no status create it
        if not available_status:
            if self.team:
                available_status = Status.objects.create(
                    name='Test Status',
                    team=self.team,
                    creator=self.user
                )
            else:
                available_status = Status.objects.create(
                    name='Test Status',
                    creator=self.user
                )

        self.tasks_data = {
            'name': 'new_test_task',
            'description': 'new_test_description',
            'status': available_status.id,
            'executor': available_executor.id,
        }

        # add labels if available
        if available_label:
            self.tasks_data['labels'] = [available_label.id]

    def _get_team_user_ids(self, user):
        """Helper method to get all user IDs from user's teams"""
        # get user's teams
        user_teams = TeamMembership.objects.filter(
            user=user
        ).values_list('team', flat=True)

        if user_teams:
            # get all users in the same teams
            return TeamMembership.objects.filter(
                team__in=user_teams
            ).values_list('user', flat=True).distinct()
        else:
            # user without team sees only their own tasks
            return [user.id]

    # list

    def test_tasks_list_response_200(self):
        response = self.c.get(reverse('tasks:tasks-list'))
        self.assertEqual(response.status_code, 200)

    def test_tasks_list_static_content(self):
        response = self.c.get(reverse('tasks:tasks-list'))
        # fields that are always visible
        self.assertContains(response, _('Tasks'))
        self.assertContains(response, _('Filter'))
        self.assertContains(response, _('Label'))

        # check that there are no titles for table if not full_view=1
        self.assertNotContains(response, f'<th scope="col">{_("ID")}</th>')
        self.assertNotContains(response, f'<th scope="col">{_("Name")}</th>')
        self.assertNotContains(response, f'<th scope="col">{_("Status")}</th>')
        self.assertNotContains(response, f'<th scope="col">{_("Author")}</th>')
        self.assertNotContains(
            response, f'<th scope="col">{_("Executor")}</th>')
        self.assertNotContains(
            response, f'<th scope="col">{_("Created at")}</th>')

    def test_tasks_list_full_view_content(self):
        response = self.c.get(reverse('tasks:tasks-list') + '?full_view=1')
        # Check if we have tasks to display
        if self.team:
            tasks = Task.objects.filter(team=self.team)
        else:
            tasks = Task.objects.filter(author=self.user, team__isnull=True)

        if tasks.exists():
            # all fields have to be visible if full_view=1 and there are tasks
            self.assertContains(response,
                                f'<th scope="col">{_("ID")}</th>')
            self.assertContains(response,
                                f'<th scope="col">{_("Name")}</th>')
            self.assertContains(response,
                                f'<th scope="col">{_("Status")}</th>')
            self.assertContains(response,
                                f'<th scope="col">{_("Author")}</th>')
            self.assertContains(response,
                                f'<th scope="col">{_("Executor")}</th>')
            self.assertContains(response,
                                f'<th scope="col">{_("Created at")}</th>')

        self.assertContains(response, _('Label'))
        self.assertContains(response, _('Tasks'))
        self.assertContains(response, _('Filter'))

    def test_tasks_list_compact_view_content(self):
        response = self.c.get(reverse('tasks:tasks-list'))
        # check for main fields visible in compact view
        self.assertContains(response, _('Tasks'))
        self.assertContains(response, _('Filter'))
        self.assertContains(response, _('Full view'))  # toggle button

        # these titles have not be visible in compact view
        self.assertNotContains(response, '<th>ID</th>')
        self.assertNotContains(response, f'<th>{_("Status")}</th>')
        self.assertNotContains(response, f'<th>{_("Author")}</th>')
        self.assertNotContains(response, f'<th>{_("Executor")}</th>')
        self.assertNotContains(response, f'<th>{_("Created at")}</th>')

    def test_tasks_list_view_toggle_buttons(self):
        # check for right buttons in compact view
        response = self.c.get(reverse('tasks:tasks-list'))
        self.assertContains(response, _('Full view'))

        # check for right buttons in compact full view
        response = self.c.get(reverse('tasks:tasks-list') + '?full_view=1')
        self.assertContains(response, _('Compact view'))

    def test_tasks_list_content(self):
        response = self.c.get(reverse('tasks:tasks-list'))

        # tasks depends of team or individual mode
        if self.team:
            tasks = Task.objects.filter(team=self.team)
            other_tasks = Task.objects.exclude(team=self.team)
        else:
            tasks = Task.objects.filter(author=self.user, team__isnull=True)
            other_tasks = (
                Task.objects.exclude(author=self.user) |
                Task.objects.filter(team__isnull=False)
            )

        for task in tasks:
            self.assertContains(response, task.name)

        for task in other_tasks:
            self.assertNotContains(response, task.name)

    def test_tasks_list_user_without_team(self):
        # create user without team
        user_no_team = User.objects.create_user(
            username='solo_user',
            password='testpass123'
        )
        self.c.force_login(user_no_team)

        # create status for user
        status = Status.objects.create(
            name='Solo Status',
            creator=user_no_team
        )

        # create task for this user
        solo_task = Task.objects.create(
            name="solo task",
            author=user_no_team,
            executor=user_no_team,
            status=status,
            team=None
        )

        response = self.c.get(reverse('tasks:tasks-list'))

        # user should see only their own task
        self.assertContains(response, solo_task.name)

        # should not see tasks from other users
        other_tasks = Task.objects.exclude(author=user_no_team)
        for task in other_tasks:
            self.assertNotContains(response, task.name)

        # cleanup
        solo_task.delete()
        status.delete()
        user_no_team.delete()

    def test_tasks_list_empty_with_message(self):
        # delete all tasks first
        Task.objects.all().delete()
        response = self.c.get(reverse('tasks:tasks-list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, _('No tasks'))
        # check that table is not rendered
        self.assertNotContains(response, '<table')

    def test_tasks_list_empty_with_message_full_view(self):
        # delete all tasks first
        Task.objects.all().delete()
        response = self.c.get(reverse('tasks:tasks-list') + '?full_view=1')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, _('No tasks'))
        # check that table is not rendered
        self.assertNotContains(response, '<table')

    def test_tasks_list_not_empty_no_message(self):
        response = self.c.get(reverse('tasks:tasks-list'))

        # check if have tasks for show
        if self.team:
            tasks_exist = Task.objects.filter(team=self.team).exists()
        else:
            tasks_exist = Task.objects.filter(
                author=self.user, team__isnull=True).exists()

        self.assertEqual(response.status_code, 200)

        if tasks_exist:
            self.assertNotContains(response, _('No tasks'))
            # check that table is rendered
            self.assertContains(response, '<table')
        else:
            self.assertContains(response, _('No tasks'))

    def test_filter_button_visible_when_filter_hidden(self):
        response = self.c.get(reverse('tasks:tasks-list'))
        self.assertContains(response, _('Filter'))

    def test_filter_visible_when_show_filter_param_present(self):
        response = self.c.get(reverse('tasks:tasks-list') + '?show_filter=1')
        self.assertContains(response, _('Hide filter'))
        # filter results button
        self.assertContains(response, _('Show'))

    def test_filter_hidden_when_hide_filter_clicked(self):
        # click on "Hide filter"
        response = self.c.get(reverse('tasks:tasks-list') + '?status=1')
        self.assertContains(response, _('Filter'))

    def test_view_toggle_buttons_preserve_filter_state(self):
        # check that when toggle view (full or compact) filter state same
        # 1. filter hidden, toggle view
        response = self.c.get(reverse('tasks:tasks-list') + '?full_view=1')
        self.assertContains(response, _('Compact view'))
        # filter button visible
        self.assertContains(response, _('Filter'))

        # 2. filter is visible, toggle view
        response = self.c.get(
            reverse('tasks:tasks-list') + '?show_filter=1&full_view=1')
        self.assertContains(response, _('Compact view'))
        # hide filter button is visible
        self.assertContains(response, _('Hide filter'))

    def test_tasks_list_has_statuses_button(self):
        response = self.c.get(reverse('tasks:tasks-list'))
        self.assertContains(response, _("Statuses"))
        self.assertContains(response, reverse('statuses:statuses-list'))

    def test_tasks_list_has_labels_button(self):
        response = self.c.get(reverse('tasks:tasks-list'))
        self.assertContains(response, _("Labels"))
        self.assertContains(response, reverse('labels:labels-list'))

    def test_new_task_button_always_visible(self):
        response = self.c.get(reverse('tasks:tasks-list'))
        self.assertContains(response, _('New task'))

        response = self.c.get(reverse('tasks:tasks-list') + '?show_filter=1')
        self.assertContains(response, _('New task'))

        response = self.c.get(reverse('tasks:tasks-list') + '?full_view=1')
        self.assertContains(response, _('New task'))

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
            f"{self.task.author.username}")
        self.assertContains(
            response,
            f"{self.task.executor.username}")
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

        # check form errors
        if response.context and 'form' in response.context:
            form = response.context['form']
            if not form.is_valid():
                self.fail(f"Form validation failed: {form.errors}")

        self.assertEqual(old_count + 1, new_count)
        self.assertEqual(response.status_code, 200)

    def test_create_task_successfully(self):
        response = self.c.post(reverse('tasks:task-create'),
                               self.tasks_data, follow=True)

        # check form errors
        if response.context and 'form' in response.context:
            form = response.context['form']
            if not form.is_valid():
                self.fail(f"Form validation failed: {form.errors}")

        task = Task.objects.filter(
            name=self.tasks_data['name']).first()

        self.assertIsNotNone(task, "Task was not created")
        self.assertEqual(task.name, self.tasks_data['name'])
        self.assertRedirects(response, reverse('tasks:tasks-list'))
        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]), _('Task created successfully'))

    def test_create_task_user_with_team_can_choose_executor(self):
        # sure that user has team
        if not self.team:
            self.skipTest("User has no team")

        response = self.c.post(reverse('tasks:task-create'),
                               self.tasks_data, follow=True)

        task = Task.objects.filter(name=self.tasks_data['name']).first()
        self.assertIsNotNone(task, "Task was not created")
        self.assertEqual(task.author, self.user)

        expected_executor = User.objects.get(pk=self.tasks_data['executor'])
        self.assertEqual(task.executor, expected_executor)

        self.assertEqual(response.status_code, 200)

    def test_create_task_user_without_team_auto_executor(self):
        # create user without team
        user_no_team = User.objects.create_user(
            username='notinteam',
            password='testpass123'
        )

        # create status for this user
        status = Status.objects.create(
            name='Personal Status',
            creator=user_no_team
        )

        self.c.force_login(user_no_team)

        task_data = {
            'name': 'solo_task',
            'description': 'task for user without team',
            'status': status.id,
            'executor': user_no_team.id,  # should be set automatically to self
            'labels': []
        }

        self.c.post(reverse('tasks:task-create'),
                               task_data, follow=True)

        task = Task.objects.filter(name=task_data['name']).first()
        self.assertIsNotNone(task, "Task was not created")

        # check that executor and author are the same
        self.assertEqual(task.author, user_no_team)
        self.assertEqual(task.executor, user_no_team)
        self.assertIsNone(task.team)

        # cleanup
        task.delete()
        status.delete()
        user_no_team.delete()

    def test_create_task_user_without_team_limited_executor_choice(self):
        # create user without team
        user_no_team = User.objects.create_user(
            username='notinteam2',
            password='testpass123'
        )
        self.c.force_login(user_no_team)

        response = self.c.get(reverse('tasks:task-create'))

        # check that executor field contains only the current user
        form = response.context.get('form')
        if form:
            executor_queryset = form.fields['executor'].queryset
            # user without team should only see themselves as executor option
            self.assertEqual(executor_queryset.count(), 1)
            self.assertEqual(executor_queryset.first(), user_no_team)
            # check that field is readonly
            self.assertTrue(
                form.fields['executor'].widget.attrs.get('readonly'))

        # cleanup
        user_no_team.delete()

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
            follow=True
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
        response = self.c.post(
            reverse('tasks:task-update', args=[task.id]),
            self.tasks_data, follow=True
        )

        # check form errors
        if response.context and 'form' in response.context:
            form = response.context['form']
            if not form.is_valid():
                self.fail(f"Form validation failed: {form.errors}")

        task.refresh_from_db()
        self.assertEqual(task.name, self.tasks_data['name'])

    def test_update_task_by_author_success(self):
        # create a task where current user is the author
        author = User.objects.get(username='me')

        # get executor and status for team
        if self.team:
            executor = User.objects.filter(
                team_memberships__team=self.team
            ).exclude(pk=author.pk).first() or author
            status = Status.objects.filter(team=self.team).first()
        else:
            executor = author
            status = Status.objects.filter(
                creator=author, team__isnull=True).first()

        if not status:
            status = Status.objects.create(
                name='Test Status for Update',
                team=self.team if self.team else None,
                creator=author
            )

        task = Task.objects.create(
            name="author task",
            author=author,
            executor=executor,
            status=status,
            team=self.team
        )

        response = self.c.post(
            reverse('tasks:task-update', args=[task.id]),
            self.tasks_data, follow=True
        )

        # check form errors
        if response.context and 'form' in response.context:
            form = response.context['form']
            if not form.is_valid():
                self.fail(f"Form validation failed: {form.errors}")

        self.assertEqual(response.status_code, 200)
        task.refresh_from_db()
        self.assertEqual(task.name, self.tasks_data['name'])

        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]), _("Task updated successfully"))

    def test_update_task_by_executor_success(self):
        # create a task where current user is the executor
        executor = User.objects.get(username='me')

        # get another user from same team as author
        if self.team:
            author = User.objects.filter(
                team_memberships__team=self.team
            ).exclude(pk=executor.pk).first() or executor
            status = Status.objects.filter(team=self.team).first()
        else:
            author = executor
            status = Status.objects.filter(
                creator=executor, team__isnull=True).first()

        if not status:
            status = Status.objects.create(
                name='Test Status for Executor Update',
                team=self.team if self.team else None,
                creator=executor
            )

        task = Task.objects.create(
            name="executor task",
            author=author,
            executor=executor,
            status=status,
            team=self.team
        )

        response = self.c.post(
            reverse('tasks:task-update', args=[task.id]),
            self.tasks_data, follow=True
        )

        # check form errors
        if response.context and 'form' in response.context:
            form = response.context['form']
            if not form.is_valid():
                self.fail(f"Form validation failed: {form.errors}")

        self.assertEqual(response.status_code, 200)
        task.refresh_from_db()
        self.assertEqual(task.name, self.tasks_data['name'])

        messages = list(get_messages(response.wsgi_request))
        self.assertGreater(len(messages), 0)
        self.assertEqual(str(messages[0]), _("Task updated successfully"))

    def test_update_task_by_neither_author_nor_executor_denied(self):
        author = User.objects.get(pk=12)  # he is not 'me'
        executor = User.objects.get(pk=13)  # and he is not 'me' too

        task = Task.objects.create(
            name="restricted task",
            author=author,
            executor=executor,
            status_id=12
        )

        # current user ('me') try update not yours task
        response = self.c.post(
            reverse('tasks:task-update', args=[task.id]),
            self.tasks_data,
            follow=True
        )

        self.assertRedirects(response, reverse('tasks:tasks-list'))

        # check for error message
        error_message = _("Task can only be updated by its author or executor.")
        self.assertContains(response, error_message)

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
