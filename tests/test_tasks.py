from task_manager.tasks.models import Task
from task_manager.user.models import User
from task_manager.teams.models import TeamMembership, Team
from task_manager.statuses.models import Status
from task_manager.labels.models import Label
from django.test import TestCase, Client
from django.urls import reverse
from django.utils.translation import gettext as _
from django.contrib.messages import get_messages


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

        # set active_team to session if user has team
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
        user_teams = TeamMembership.objects.filter(
            user=user
        ).values_list('team', flat=True)

        if user_teams:
            return TeamMembership.objects.filter(
                team__in=user_teams
            ).values_list('user', flat=True).distinct()
        else:
            return [user.id]

    # ========== LIST VIEW TESTS ==========

    def test_tasks_list_response_200(self):
        response = self.c.get(reverse('tasks:tasks-list'))
        self.assertEqual(response.status_code, 200)

    def test_tasks_list_has_page_title(self):
        """Check that page has main title"""
        response = self.c.get(reverse('tasks:tasks-list'))
        self.assertContains(response, _('Tasks'))

    def test_tasks_list_has_create_button(self):
        """Check that 'New task' button is always visible"""
        response = self.c.get(reverse('tasks:tasks-list'))
        self.assertContains(response, _('New task'))
        self.assertContains(response, reverse('tasks:task-create'))

    def test_tasks_list_has_statuses_link(self):
        """Check that Statuses link is visible"""
        response = self.c.get(reverse('tasks:tasks-list'))
        self.assertContains(response, _("Statuses"))
        self.assertContains(response, reverse('statuses:statuses-list'))

    def test_tasks_list_has_labels_link(self):
        """Check that Labels link is visible"""
        response = self.c.get(reverse('tasks:tasks-list'))
        self.assertContains(response, _("Labels"))
        self.assertContains(response, reverse('labels:labels-list'))

    def test_tasks_list_has_filter_button(self):
        """Check that Filter button is visible when filter is hidden"""
        response = self.c.get(reverse('tasks:tasks-list'))
        self.assertContains(response, _('Filter'))

    def test_tasks_list_has_hide_filter_button(self):
        """Check that 'Hide filter' button is visible when filter is shown"""
        response = self.c.get(reverse('tasks:tasks-list') + '?show_filter=1')
        self.assertContains(response, _('Hide filter'))

    def test_tasks_list_filter_form_visible(self):
        """Check that filter form is visible when show_filter=1"""
        response = self.c.get(reverse('tasks:tasks-list') + '?show_filter=1')
        self.assertContains(response, 'id="filter-form"')
        self.assertContains(response, _('Apply'))
        self.assertContains(response, _('Reset'))

    def test_tasks_list_filter_form_hidden(self):
        """Check that filter form is hidden by default"""
        response = self.c.get(reverse('tasks:tasks-list'))
        self.assertNotContains(response, 'id="filter-form"')

    def test_tasks_list_shows_task_cards(self):
        """Check that tasks are displayed as cards"""
        response = self.c.get(reverse('tasks:tasks-list'))

        if self.team:
            tasks_exist = Task.objects.filter(team=self.team).exists()
        else:
            tasks_exist = Task.objects.filter(
                author=self.user, team__isnull=True).exists()

        if tasks_exist:
            self.assertContains(response, 'task-card')
            # Check that table is NOT used (we use cards now)
            self.assertNotContains(response, '<table')

    def test_tasks_list_card_shows_task_name(self):
        """Check that task name is visible in card"""
        response = self.c.get(reverse('tasks:tasks-list'))

        if self.team:
            task = Task.objects.filter(team=self.team).first()
        else:
            task = Task.objects.filter(
                author=self.user, team__isnull=True).first()

        if task:
            self.assertContains(response, task.name)

    def test_tasks_list_card_shows_task_id(self):
        """Check that task ID is visible in card"""
        response = self.c.get(reverse('tasks:tasks-list'))

        if self.team:
            task = Task.objects.filter(team=self.team).first()
        else:
            task = Task.objects.filter(
                author=self.user, team__isnull=True).first()

        if task:
            self.assertContains(response, f'#{task.id}')

    def test_tasks_list_card_shows_status(self):
        """Check that task status is visible in card"""
        response = self.c.get(reverse('tasks:tasks-list'))

        if self.team:
            task = Task.objects.filter(team=self.team).first()
        else:
            task = Task.objects.filter(
                author=self.user, team__isnull=True).first()

        if task and task.status:
            self.assertContains(response, task.status.name)

    def test_tasks_list_card_shows_author(self):
        """Check that task author is visible in card"""
        response = self.c.get(reverse('tasks:tasks-list'))

        if self.team:
            task = Task.objects.filter(team=self.team).first()
        else:
            task = Task.objects.filter(
                author=self.user, team__isnull=True).first()

        if task:
            self.assertContains(response, task.author.username)

    def test_tasks_list_card_shows_executor(self):
        """Check that executor or 'No assignee' is visible in card"""
        response = self.c.get(reverse('tasks:tasks-list'))

        if self.team:
            task = Task.objects.filter(team=self.team).first()
        else:
            task = Task.objects.filter(
                author=self.user, team__isnull=True).first()

        if task:
            if task.executor:
                self.assertContains(response, task.executor.username)
            else:
                self.assertContains(response, _('No assignee'))

    def test_tasks_list_card_shows_date(self):
        """Check that creation date is visible in card"""
        response = self.c.get(reverse('tasks:tasks-list'))

        if self.team:
            task = Task.objects.filter(team=self.team).first()
        else:
            task = Task.objects.filter(
                author=self.user, team__isnull=True).first()

        if task:
            # Check date format d.m.y (e.g., 15.01.25)
            date_str = task.created_at.strftime("%d.%m.%y")
            self.assertContains(response, date_str)

    def test_tasks_list_card_shows_description_preview(self):
        """Check that description preview is visible if task has description"""
        # Create task with description
        status = Status.objects.filter(team=self.team).first() \
            if self.team else \
            Status.objects.filter(
                creator=self.user,
                team__isnull=True).first()

        if not status:
            status = Status.objects.create(
                name='Test Status',
                team=self.team,
                creator=self.user
            )

        task = Task.objects.create(
            name="Task with description",
            description="This is a test description for preview",
            author=self.user,
            executor=self.user,
            status=status,
            team=self.team
        )

        response = self.c.get(reverse('tasks:tasks-list'))
        self.assertContains(response, "This is a test description")

        # cleanup
        task.delete()

    def test_tasks_list_card_shows_labels(self):
        """Check that labels are visible in card"""
        if self.team:
            label = Label.objects.filter(team=self.team).first()
            status = Status.objects.filter(team=self.team).first()
        else:
            label = Label.objects.filter(
                creator=self.user, team__isnull=True).first()
            status = Status.objects.filter(
                creator=self.user, team__isnull=True).first()

        if not label or not status:
            self.skipTest("No labels or status available")

        task = Task.objects.create(
            name="Task with label",
            author=self.user,
            executor=self.user,
            status=status,
            team=self.team
        )
        task.labels.add(label)

        response = self.c.get(reverse('tasks:tasks-list'))
        self.assertContains(response, label.name)

        # cleanup
        task.delete()

    def test_tasks_list_card_has_link_to_update(self):
        """Check that task card links to update page"""
        response = self.c.get(reverse('tasks:tasks-list'))

        if self.team:
            task = Task.objects.filter(team=self.team).first()
        else:
            task = Task.objects.filter(
                author=self.user, team__isnull=True).first()

        if task:
            update_url = reverse('tasks:task-update', args=[task.id])
            self.assertContains(response, update_url)

    def test_tasks_list_shows_task_count(self):
        """Check that task count is displayed"""
        response = self.c.get(reverse('tasks:tasks-list'))

        if self.team:
            count = Task.objects.filter(team=self.team).count()
        else:
            count = Task.objects.filter(
                author=self.user, team__isnull=True).count()

        if count > 0:
            self.assertContains(response, f'{count} task')

    def test_tasks_list_empty_state(self):
        """Check empty state message when no tasks"""
        Task.objects.all().delete()
        response = self.c.get(reverse('tasks:tasks-list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, _('No tasks'))
        # self.assertNotContains(response, 'task-card')

    def test_tasks_list_empty_state_has_create_button(self):
        """Check that empty state has create task button"""
        Task.objects.all().delete()
        response = self.c.get(reverse('tasks:tasks-list'))
        self.assertContains(response, _('Create Task'))
        self.assertContains(response, reverse('tasks:task-create'))

    def test_tasks_list_filter_active_indicator(self):
        """Check that 'Filters active' badge is shown
          when filter is hidden but has params"""
        # Apply filter, then hide filter panel
        response = self.c.get(
            reverse('tasks:tasks-list') + '?status=1')
        self.assertContains(response, _('Filters active'))

    def test_tasks_list_filter_active_indicator_not_shown_when_no_params(self):
        """Check that 'Filters active' badge
         is NOT shown when no filter params"""
        response = self.c.get(reverse('tasks:tasks-list'))
        self.assertNotContains(response, _('Filters active'))

    def test_tasks_list_filter_indicator_not_shown_when_filter_visible(self):
        """Check that 'Filters active' badge
         is NOT shown when filter panel is visible"""
        response = self.c.get(
            reverse('tasks:tasks-list') + '?show_filter=1&status=1')
        self.assertNotContains(response, _('Filters active'))

    def test_new_task_button_visible_when_filter_shown(self):
        """Check that 'New task' button is visible even when filter is shown"""
        response = self.c.get(reverse('tasks:tasks-list') + '?show_filter=1')
        self.assertContains(response, _('New task'))

    # ========== CREATE TASK TESTS ==========

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

        if response.context and 'form' in response.context:
            form = response.context['form']
            if not form.is_valid():
                self.fail(f"Form validation failed: {form.errors}")

        self.assertEqual(old_count + 1, new_count)
        self.assertEqual(response.status_code, 200)

    def test_create_task_successfully(self):
        response = self.c.post(reverse('tasks:task-create'),
                               self.tasks_data, follow=True)

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
        user_no_team = User.objects.create_user(
            username='notinteam',
            password='testpass123'
        )

        status = Status.objects.create(
            name='Personal Status',
            creator=user_no_team
        )

        self.c.force_login(user_no_team)

        task_data = {
            'name': 'solo_task',
            'description': 'task for user without team',
            'status': status.id,
            'executor': user_no_team.id,
            'labels': []
        }

        self.c.post(reverse('tasks:task-create'), task_data, follow=True)

        task = Task.objects.filter(name=task_data['name']).first()
        self.assertIsNotNone(task, "Task was not created")

        self.assertEqual(task.author, user_no_team)
        self.assertEqual(task.executor, user_no_team)
        self.assertIsNone(task.team)

        # cleanup
        task.delete()
        status.delete()
        user_no_team.delete()

    def test_create_task_user_solo_in_team_auto_executor(self):
        solo_user = User.objects.create_user(
            username='solo_team_user',
            password='testpass123'
        )

        team = Team.objects.create(
            name='Solo Team',
            description='Team with single member'
        )

        TeamMembership.objects.create(
            user=solo_user,
            team=team,
            role='admin'
        )

        self.c.force_login(solo_user)

        session = self.c.session
        session['active_team_id'] = team.id
        session.save()

        available_status = Status.objects.filter(team=team).first()
        if not available_status:
            available_status = Status.objects.create(
                name='Test Status',
                team=team,
                creator=solo_user
            )

        available_executor = User.objects.filter(
            team_memberships__team=team
        ).exclude(pk=solo_user.pk).first() or solo_user

        task_data = {
            'name': 'solo_team_task',
            'description': 'task for solo team user',
            'status': available_status.id,
            'executor': available_executor.id,
        }

        self.c.post(reverse('tasks:task-create'), task_data, follow=True)

        task = Task.objects.filter(name=task_data['name']).first()
        self.assertIsNotNone(task, "Task was not created")

        self.assertEqual(task.author, solo_user)
        self.assertEqual(task.executor, solo_user)
        self.assertEqual(task.team, team)

        # cleanup
        task.delete()
        if available_status:
            available_status.delete()
        TeamMembership.objects.filter(user=solo_user, team=team).delete()
        team.delete()
        solo_user.delete()

    def test_create_task_user_without_team_limited_executor_choice(self):
        user_no_team = User.objects.create_user(
            username='notinteam2',
            password='testpass123'
        )
        self.c.force_login(user_no_team)

        response = self.c.get(reverse('tasks:task-create'))

        form = response.context.get('form')
        if form:
            executor_queryset = form.fields['executor'].queryset
            self.assertEqual(executor_queryset.count(), 1)
            self.assertEqual(executor_queryset.first(), user_no_team)
            self.assertTrue(
                form.fields['executor'].widget.attrs.get('readonly'))

        # cleanup
        user_no_team.delete()

    # ========== UPDATE TASK TESTS ==========

    def test_task_update_view_response_200(self):
        response = self.c.get(
            reverse('tasks:task-update', args=[self.task.id]))
        self.assertEqual(response.status_code, 200)

    def test_task_update_view_static_content(self):
        response = self.c.get(
            reverse('tasks:task-update', args=[self.task.id]))
        self.assertContains(response, self.task.name)
        self.assertContains(response, _('Name'))
        self.assertContains(response, _('Description'))
        self.assertContains(response, _('Status'))
        self.assertContains(response, _('Executor'))
        self.assertContains(response, _('Labels'))
        self.assertContains(response, _("Edit"))
        self.assertContains(response, ("Delete"))
        self.assertContains(response, _("Cancel"))

    def test_task_update_view_shows_task_id(self):
        """Check that task ID is visible on update page"""
        response = self.c.get(
            reverse('tasks:task-update', args=[self.task.id]))
        self.assertContains(response, _('ID'))
        self.assertContains(response, str(self.task.id))

    def test_task_update_view_shows_author(self):
        """Check that author is visible on update page"""
        response = self.c.get(
            reverse('tasks:task-update', args=[self.task.id]))
        self.assertContains(response, self.task.author.username)

    def test_task_update_has_cancel_button(self):
        """Check that Cancel button exists and links to tasks list"""
        response = self.c.get(
            reverse('tasks:task-update', args=[self.task.id]))
        self.assertContains(response, _('Cancel'))
        list_url = reverse('tasks:tasks-list')
        self.assertIn(list_url, response.content.decode('utf-8'))

    def test_task_update_has_delete_button(self):
        """Check that Delete button exists and links to delete page"""
        response = self.c.get(
            reverse('tasks:task-update', args=[self.task.id]))
        self.assertContains(response, _('Delete'))
        delete_url = reverse('tasks:task-delete', args=[self.task.id])
        self.assertIn(delete_url, response.content.decode('utf-8'))

    def test_update_task_response_200(self):
        task = Task.objects.get(name="first task")
        response = self.c.post(
            reverse('tasks:task-update', args=[task.id]),
            self.tasks_data, follow=True
        )
        self.assertEqual(response.status_code, 200)

    def test_update_task_with_correct_data(self):
        task = Task.objects.get(name="first task")
        response = self.c.post(
            reverse('tasks:task-update', args=[task.id]),
            self.tasks_data, follow=True
        )

        if response.context and 'form' in response.context:
            form = response.context['form']
            if not form.is_valid():
                self.fail(f"Form validation failed: {form.errors}")

        task.refresh_from_db()
        self.assertEqual(task.name, self.tasks_data['name'])

    def test_update_task_by_author_success(self):
        author = User.objects.get(username='me')

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
        executor = User.objects.get(username='me')

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
        author = User.objects.get(pk=12)
        executor = User.objects.get(pk=13)

        task = Task.objects.create(
            name="restricted task",
            author=author,
            executor=executor,
            status_id=12
        )

        response = self.c.post(
            reverse('tasks:task-update', args=[task.id]),
            self.tasks_data,
            follow=True
        )

        self.assertRedirects(response, reverse('tasks:tasks-list'))

        error_message = _("Task can only be updated by its author or executor.")
        self.assertContains(response, error_message)

    # ========== DELETE TASK TESTS ==========

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

    def test_delete_task_has_cancel_button(self):
        """Check that Cancel button exists on delete page"""
        task = Task.objects.get(name="first task")
        response = self.c.get(reverse('tasks:task-delete',
                              args=[task.id]), follow=True)
        self.assertContains(response, _('Cancel'))

    def test_delete_task_cancel_button_redirects_to_referer(self):
        """Check that Cancel button uses HTTP_REFERER"""
        task = Task.objects.get(name="first task")

        response = self.c.get(
            reverse('tasks:task-delete', args=[task.id]),
            HTTP_REFERER=reverse('tasks:tasks-list'),
            follow=True
        )

        self.assertContains(response, _('Cancel'))

        cancel_url = reverse('tasks:tasks-list')
        self.assertIn(cancel_url, response.content.decode('utf-8'))

    def test_delete_task_cancel_button_without_referer(self):
        """Check that Cancel button goes to home when no referer"""
        task = Task.objects.get(name="first task")

        response = self.c.get(
            reverse('tasks:task-delete', args=[task.id]),
            follow=True
        )

        self.assertContains(response, _('Cancel'))
        self.assertIn('href="/"', response.content.decode('utf-8'))

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
