import warnings
from datetime import date
from task_manager.tasks.models import Task
from task_manager.statuses.models import Status
from task_manager.labels.models import Label
from task_manager.user.models import User
from task_manager.teams.models import TeamMembership
from django.test import TestCase, Client
from django.urls import reverse


class TaskTestCase(TestCase):
    fixtures = ["tests/fixtures/test_teams.json",
                "tests/fixtures/test_users.json",
                "tests/fixtures/test_teams_memberships.json",
                "tests/fixtures/test_statuses.json",
                "tests/fixtures/test_tasks.json",
                "tests/fixtures/test_labels.json"
                ]

    def setUp(self):
        self.user = User.objects.get(username='he')  # id=12
        self.status = Status.objects.get(name='at work')
        self.label = Label.objects.get(name='bug')
        self.c = Client()
        self.c.force_login(self.user)

        membership = TeamMembership.objects.filter(user=self.user).first()
        self.team = membership.team if membership else None

        # set active_team_id in session if team is set
        if self.team:
            session = self.c.session
            session['active_team_id'] = self.team.id
            session.save()

        # filter tasks by status, executor, label and team
        if self.team:
            self.filtered_tasks = Task.objects.filter(
                executor=self.user,
                status=self.status,
                labels=self.label,
                team=self.team
            )
        else:
            self.filtered_tasks = Task.objects.filter(
                executor=self.user,
                status=self.status,
                labels=self.label,
                team__isnull=True
            )

        self.response = self.c.get(reverse('tasks:tasks-list'),
                                   {'executor': self.user.id,
                                    'status': self.status.id,
                                    'labels': self.label.id
                                    })

        # Ignore naive datetime field warnings at filtering
        warnings.filterwarnings(
            "ignore",
            category=RuntimeWarning,
            module='django.db.models.fields',
            message=r'DateTimeField .* received a naive datetime'
        )

    def test_task_list_response_200(self):
        self.assertEqual(self.response.status_code, 200)

    def test_filter_tasks_by_status_executor_label(self):
        filtered_task_ids = list(
            self.filtered_tasks.values_list('id', flat=True)
        )

        self.assertIn('filter', self.response.context)

        response_task_ids = list(
            self.response.context['filter'].qs.values_list('id', flat=True)
        )

        self.assertListEqual(
            sorted(filtered_task_ids),
            sorted(response_task_ids)
        )

    def test_filter_own_tasks(self):
        user = User.objects.get(username="me")  # id=10
        self.c.logout()
        self.c.force_login(user)

        membership = TeamMembership.objects.filter(user=user).first()
        team = membership.team if membership else None

        # set active_team_id in session if team is set
        if team:
            session = self.c.session
            session['active_team_id'] = team.id
            session.save()

        # make request with self_tasks=on to filter own tasks
        response = self.c.get(reverse('tasks:tasks-list'), {'self_tasks': 'on'})

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs

        # check if all tasks are from user
        for task in filtered_tasks:
            self.assertEqual(task.author, user)

    def test_filter_by_status_only(self):
        """Test filtering by status only"""
        response = self.c.get(reverse('tasks:tasks-list'),
                              {'status': self.status.id})

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs
        for task in filtered_tasks:
            self.assertEqual(task.status, self.status)

    def test_filter_by_executor_only(self):
        """Test filtering by executor only"""
        response = self.c.get(reverse('tasks:tasks-list'),
                              {'executor': self.user.id})

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs
        for task in filtered_tasks:
            self.assertEqual(task.executor, self.user)

    def test_filter_by_label_only(self):
        """Test filtering by label only"""
        response = self.c.get(reverse('tasks:tasks-list'),
                              {'labels': self.label.id})

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs
        for task in filtered_tasks:
            self.assertIn(self.label, task.labels.all())

    def test_empty_filter(self):
        """Test that empty filter returns all available tasks"""
        response = self.c.get(reverse('tasks:tasks-list'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs

        # get all tasks available for user
        if self.team:
            expected_tasks = Task.objects.filter(team=self.team)
        else:
            expected_tasks = Task.objects.filter(
                author=self.user, team__isnull=True
            )

        self.assertEqual(filtered_tasks.count(), expected_tasks.count())

    def test_filter_without_team(self):
        """Test filter for user without team"""
        user_no_team = User.objects.create_user(
            username='no_team_user',
            password='testpass123'
        )

        status = Status.objects.create(
            name='Personal Status',
            creator=user_no_team
        )

        task = Task.objects.create(
            name='Personal Task',
            author=user_no_team,
            executor=user_no_team,
            status=status,
            team=None
        )

        self.c.logout()
        self.c.force_login(user_no_team)

        # request without filters
        response = self.c.get(reverse('tasks:tasks-list'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs

        # user with no team has to see only his task
        self.assertEqual(filtered_tasks.count(), 1)
        self.assertEqual(filtered_tasks.first(), task)

        # cleanup
        task.delete()
        status.delete()
        user_no_team.delete()

    def test_filter_by_created_after(self):
        """Test filtering by created_after date"""
        # 2024-04-05T16:09:14.936Z is the earliest task date in fixtures
        response = self.c.get(reverse('tasks:tasks-list'),
                              {'created_after': '2024-04-06'})

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs

        for task in filtered_tasks:
            self.assertGreaterEqual(task.created_at.date(), date(2024, 4, 6))

    def test_filter_by_created_before(self):
        """Test filtering by created_before date"""
        # 2024-04-05T16:09:14.936Z is the earliest task date in fixtures
        response = self.c.get(reverse('tasks:tasks-list'),
                              {'created_before': '2024-04-05'})

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs

        for task in filtered_tasks:
            self.assertLessEqual(task.created_at.date(), date(2024, 4, 5))

    def test_filter_by_date_range(self):
        """Test filtering by created_after and created_before together"""
        response = self.c.get(reverse('tasks:tasks-list'), {
            'created_after': '2024-04-05',
            'created_before': '2024-04-06'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs

        for task in filtered_tasks:
            self.assertGreaterEqual(task.created_at.date(), date(2024, 4, 5))
            self.assertLessEqual(task.created_at.date(), date(2024, 4, 6))

    def test_filter_exclude_by_status(self):
        """Test exclude mode for status filter"""
        # Get a different status to exclude
        other_status = Status.objects.exclude(pk=self.status.pk).first()
        if not other_status:
            self.skipTest("No other status available for exclude test")

        response = self.c.get(reverse('tasks:tasks-list'), {
            'status': other_status.pk,
            'status_exclude': 'on'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs

        # All tasks should NOT have the excluded status
        for task in filtered_tasks:
            self.assertNotEqual(task.status, other_status)

    def test_filter_exclude_by_executor(self):
        """Test exclude mode for executor filter"""
        # Get another user who is executor of some tasks
        other_user = User.objects.exclude(pk=self.user.pk).first()
        if not other_user:
            self.skipTest("No other user available for exclude test")

        response = self.c.get(reverse('tasks:tasks-list'), {
            'executor': other_user.pk,
            'executor_exclude': 'on'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs

        # All tasks should NOT have the excluded executor
        for task in filtered_tasks:
            self.assertNotEqual(task.executor, other_user)

    def test_filter_exclude_by_label(self):
        """Test exclude mode for label filter"""
        # Get another label to exclude
        other_label = Label.objects.exclude(pk=self.label.pk).first()
        if not other_label:
            self.skipTest("No other label available for exclude test")

        response = self.c.get(reverse('tasks:tasks-list'), {
            'labels': other_label.pk,
            'labels_exclude': 'on'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs

        # All tasks should NOT have the excluded label
        for task in filtered_tasks:
            self.assertNotIn(other_label, task.labels.all())

    def test_filter_exclude_own_tasks(self):
        """Test exclude mode for self_tasks filter"""
        response = self.c.get(reverse('tasks:tasks-list'), {
            'self_tasks': 'on',
            'self_tasks_exclude': 'on'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs

        # All tasks should NOT be authored by the current user
        for task in filtered_tasks:
            self.assertNotEqual(task.author, self.user)

    def test_filter_combined_with_exclude(self):
        """Test combining regular filter with exclude filter"""
        other_status = Status.objects.exclude(pk=self.status.pk).first()
        if not other_status:
            self.skipTest("No other status available for combined test")

        response = self.c.get(reverse('tasks:tasks-list'), {
            'status': other_status.pk,
            'status_exclude': 'on',
            'executor': self.user.id
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs

        # Tasks should have the specified executor
        for task in filtered_tasks:
            self.assertEqual(task.executor, self.user)
            # And should NOT have the excluded status
            self.assertNotEqual(task.status, other_status)

    def test_filter_exclude_invalid_value(self):
        """Test exclude filter with invalid value (should behave as include)"""
        # Using invalid exclude value should work as normal include
        response = self.c.get(reverse('tasks:tasks-list'), {
            'status': self.status.pk,
            'status_exclude': 'invalid_value'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs

        # Should include tasks with the status (not exclude)
        for task in filtered_tasks:
            self.assertEqual(task.status, self.status)

    def test_filter_date_edge_case_same_day(self):
        """Test date filter when created_after equals created_before"""
        response = self.c.get(reverse('tasks:tasks-list'), {
            'created_after': '2024-04-05',
            'created_before': '2024-04-05'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs

        # Should return tasks created on that specific day
        for task in filtered_tasks:
            self.assertEqual(task.created_at.date(), date(2024, 4, 5))

    def test_filter_no_matching_date(self):
        """Test date filter with range that matches no tasks"""
        response = self.c.get(reverse('tasks:tasks-list'), {
            'created_after': '2025-01-01',
            'created_before': '2025-12-31'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs

        # Should return empty queryset
        self.assertEqual(filtered_tasks.count(), 0)

    def test_filter_exclude_self_tasks_with_other_filters(self):
        """Test exclude self_tasks combined with other filters"""
        other_status = Status.objects.exclude(pk=self.status.pk).first()
        if not other_status:
            self.skipTest("No other status available for this test")

        response = self.c.get(reverse('tasks:tasks-list'), {
            'self_tasks': 'on',
            'self_tasks_exclude': 'on',
            'status': self.status.pk
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('filter', response.context)

        filtered_tasks = response.context['filter'].qs

        # Tasks should NOT be authored by current user
        # And should have the specified status
        for task in filtered_tasks:
            self.assertNotEqual(task.author, self.user)
            self.assertEqual(task.status, self.status)

    # Tests for filter button UI logic
    def test_filter_button_shows_count_with_active_filters(self):
        """Test that filter button shows correct count
        when filters are active"""
        response = self.c.get(reverse('tasks:tasks-list'), {
            'status': self.status.id,
            'executor': self.user.id
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('active_filter_count', response.context)
        self.assertEqual(response.context['active_filter_count'], 2)

    def test_filter_button_shows_zero_count_no_filters(self):
        """Test that filter button shows zero count
        when no filters are active"""
        response = self.c.get(reverse('tasks:tasks-list'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('active_filter_count', response.context)
        self.assertEqual(response.context['active_filter_count'], 0)

    def test_filter_button_shows_count_single_filter(self):
        """Test that filter button shows count 1 for single active filter"""
        response = self.c.get(reverse('tasks:tasks-list'), {
            'status': self.status.id
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('active_filter_count', response.context)
        self.assertEqual(response.context['active_filter_count'], 1)

    def test_filter_button_exclude_mode_counts_as_active(self):
        """Test that exclude mode parameters are counted as active filters"""
        response = self.c.get(reverse('tasks:tasks-list'), {
            'status': self.status.id,
            'status_exclude': 'on'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('active_filter_count', response.context)
        self.assertEqual(response.context['active_filter_count'], 2)

    def test_filter_button_multiple_exclude_filters(self):
        """Test counting multiple exclude filters correctly"""
        response = self.c.get(reverse('tasks:tasks-list'), {
            'status': self.status.id,
            'executor': self.user.id,
            'status_exclude': 'on',
            'executor_exclude': 'on'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('active_filter_count', response.context)
        self.assertEqual(response.context['active_filter_count'], 4)

    def test_filter_button_date_filters_counted(self):
        """Test that date filters are counted correctly"""
        response = self.c.get(reverse('tasks:tasks-list'), {
            'created_after': '2024-04-01',
            'created_before': '2024-04-30'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('active_filter_count', response.context)
        self.assertEqual(response.context['active_filter_count'], 2)

    def test_filter_button_service_params_not_counted(self):
        """Test that service parameters are not counted as active filters"""
        response = self.c.get(reverse('tasks:tasks-list'), {
            'status': self.status.id,
            'show_filter': '1',
            'save_as_default': 'on'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('active_filter_count', response.context)
        # Only status should be counted, not service parameters
        self.assertEqual(response.context['active_filter_count'], 1)

    def test_filter_button_empty_values_not_counted(self):
        """Test that empty filter values are not counted"""
        response = self.c.get(reverse('tasks:tasks-list'), {
            'status': self.status.id,
            'executor': '',
            'labels': ''
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('active_filter_count', response.context)
        # Only status should be counted (executor and labels empty)
        self.assertEqual(response.context['active_filter_count'], 1)

    # Tests for default filter mode display
    def test_saved_filter_enabled_context(self):
        """Test that saved filter enabled state is passed to context"""
        # First save a filter as default
        session = self.c.session
        session['task_filter_params'] = {'status': self.status.id}
        session['task_filter_enabled'] = True
        session.save()

        response = self.c.get(reverse('tasks:tasks-list'), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('saved_filter_enabled', response.context)
        self.assertTrue(response.context['saved_filter_enabled'])

    def test_saved_filter_params_context(self):
        """Test that saved filter parameters are passed to context"""
        saved_params = {'status': self.status.id, 'executor': self.user.id}

        session = self.c.session
        session['task_filter_params'] = saved_params
        session['task_filter_enabled'] = True
        session.save()

        response = self.c.get(reverse('tasks:tasks-list'), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('saved_filter_params', response.context)
        self.assertEqual(response.context['saved_filter_params'], saved_params)

    def test_has_saved_filter_false_when_no_saved_params(self):
        """Test that has_saved_filter is False when no saved parameters exist"""
        # Clear any existing saved filters
        session = self.c.session
        session.pop('task_filter_params', None)
        session.pop('task_filter_enabled', None)
        session.save()

        response = self.c.get(reverse('tasks:tasks-list'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('has_saved_filter', response.context)
        self.assertFalse(response.context['has_saved_filter'])

    def test_has_saved_filter_true_with_saved_params(self):
        """Test that has_saved_filter is True when saved parameters exist"""
        session = self.c.session
        session['task_filter_params'] = {'status': self.status.id}
        session['task_filter_enabled'] = True
        session.save()

        response = self.c.get(reverse('tasks:tasks-list'), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('has_saved_filter', response.context)
        self.assertTrue(response.context['has_saved_filter'])

    def test_saved_filter_enabled_false_when_not_enabled(self):
        """Test saved_filter_enabled is False when filter is not enabled"""
        session = self.c.session
        session['task_filter_params'] = {'status': self.status.id}
        session['task_filter_enabled'] = False
        session.save()

        response = self.c.get(reverse('tasks:tasks-list'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('saved_filter_enabled', response.context)
        self.assertFalse(response.context['saved_filter_enabled'])

    def test_saved_filter_with_active_params_count(self):
        """Test active_filter_count when saved filter is active"""
        # Save filter parameters and enable it
        session = self.c.session
        session['task_filter_params'] = {'status': self.status.id}
        session['task_filter_enabled'] = True
        session.save()

        # Request without new filter params (should apply saved filter)
        response = self.c.get(reverse('tasks:tasks-list'), follow=True)

        self.assertEqual(response.status_code, 200)
        # When saved filter is applied, it should show the count of saved params
        self.assertIn('active_filter_count', response.context)
        self.assertEqual(response.context['active_filter_count'], 1)

    # Tests to cover missing lines in filters.py
    def test_filter_init_with_none_request(self):
        """Test filter initialization when request is None"""
        from task_manager.tasks.filters import TaskFilter
        from django.test import RequestFactory
        
        # Create filter without request (request=None)
        factory = RequestFactory()
        request = factory.get('/')
        request.user = self.user
        
        # Create filter instance directly (bypassing normal initialization)
        filter_instance = TaskFilter()
        filter_instance.request = None  # Simulate None request
        
        # This should not crash and should return early
        try:
            filter_instance.__init__()  # Call with None request
        except Exception:
            self.fail("Filter should handle None request gracefully")

    def test_get_filter_value_with_invalid_form(self):
        """Test _get_filter_value when form is not valid"""
        from task_manager.tasks.filters import TaskFilter
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/', {'status': self.status.id})
        request.user = self.user
        
        # Create filter with invalid form data
        filter_instance = TaskFilter(request.GET, queryset=Task.objects.all())
        filter_instance.request = request
        
        # Mock form as invalid
        filter_instance.form.is_valid = lambda: False
        
        # Test getting filter value when form is invalid
        value = filter_instance._get_filter_value('status')
        # Should return initial value when form is invalid
        self.assertIsNone(value)

    def test_get_filter_value_with_valid_form(self):
        """Test _get_filter_value when form is valid"""
        from task_manager.tasks.filters import TaskFilter
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/', {'status': self.status.id})
        request.user = self.user
        
        # Create filter with valid form data
        filter_instance = TaskFilter(request.GET, queryset=Task.objects.all())
        filter_instance.request = request
        
        # Mock form as valid with cleaned_data
        filter_instance.form.is_valid = lambda: True
        filter_instance.form.cleaned_data = {'status': self.status}
        
        # Test getting filter value when form is valid
        value = filter_instance._get_filter_value('status')
        self.assertEqual(value, self.status)

    def test_apply_model_filter_with_empty_value(self):
        """Test _apply_model_filter when filter value is empty"""
        from task_manager.tasks.filters import TaskFilter
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/')
        request.user = self.user
        
        filter_instance = TaskFilter(queryset=Task.objects.all())
        filter_instance.request = request
        
        # Mock _get_filter_value to return empty value
        filter_instance._get_filter_value = lambda x: None
        
        # Test applying filter with empty value
        queryset = Task.objects.all()
        result = filter_instance._apply_model_filter(queryset, 'status')
        
        # Should return original queryset when value is empty
        self.assertEqual(result, queryset)

    def test_is_excluded_with_valid_values(self):
        """Test _is_excluded with various valid exclude values"""
        from task_manager.tasks.filters import TaskFilter
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/', {'status_exclude': 'on'})
        request.user = self.user
        
        filter_instance = TaskFilter(request.GET, queryset=Task.objects.all())
        filter_instance.request = request
        
        # Test various valid exclude values
        valid_values = ['on', 'true', '1', 'checked']
        for value in valid_values:
            with self.subTest(value=value):
                # Mock form data
                filter_instance.form.data = {'status_exclude': value}
                self.assertTrue(filter_instance._is_excluded('status_exclude'))

    def test_is_excluded_with_invalid_values(self):
        """Test _is_excluded with invalid values"""
        from task_manager.tasks.filters import TaskFilter
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/', {'status_exclude': 'invalid'})
        request.user = self.user
        
        filter_instance = TaskFilter(request.GET, queryset=Task.objects.all())
        filter_instance.request = request
        
        # Test invalid exclude values
        invalid_values = ['invalid', '', 'off', 'false', '0']
        for value in invalid_values:
            with self.subTest(value=value):
                # Mock form data
                filter_instance.form.data = {'status_exclude': value}
                self.assertFalse(filter_instance._is_excluded('status_exclude'))

    def test_get_filter_value_returns_none_value(self):
        """Test _get_filter_value when cleaned_data contains None value"""
        from task_manager.tasks.filters import TaskFilter
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/')
        request.user = self.user
        
        filter_instance = TaskFilter(queryset=Task.objects.all())
        filter_instance.request = request
        
        # Mock form as valid with None value
        filter_instance.form.is_valid = lambda: True
        filter_instance.form.cleaned_data = {'status': None}
        
        # Test getting filter value when value is None
        value = filter_instance._get_filter_value('status')
        # Should return None when cleaned_data contains None
        self.assertIsNone(value)

    def test_get_base_queryset_with_team(self):
        """Test _get_base_queryset when team is available"""
        from task_manager.tasks.filters import TaskFilter
        from django.test import RequestFactory
        from task_manager.teams.models import Team
        
        # Use existing team from fixtures
        team = Team.objects.get(pk=1)
        
        factory = RequestFactory()
        request = factory.get('/')
        request.user = self.user
        request.active_team = team
        
        filter_instance = TaskFilter(queryset=Task.objects.all())
        filter_instance.request = request
        
        # Test getting base queryset with team
        queryset = filter_instance._get_base_queryset()
        
        # Should return tasks filtered by team
        self.assertTrue(queryset.filter(team=team).exists())

    def test_apply_model_filter_with_exclude_mode(self):
        """Test _apply_model_filter in exclude mode"""
        from task_manager.tasks.filters import TaskFilter
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/', {
            'status': self.status.id,
            'status_exclude': 'on'
        })
        request.user = self.user
        
        filter_instance = TaskFilter(request.GET, queryset=Task.objects.all())
        filter_instance.request = request
        
        # Mock _get_filter_value to return status
        filter_instance._get_filter_value = lambda x: self.status
        
        # Test applying filter with exclude mode
        queryset = Task.objects.all()
        result = filter_instance._apply_model_filter(queryset, 'status')
        
        # Should exclude tasks with the specified status
        self.assertFalse(result.filter(status=self.status).exists())

    def test_filter_own_tasks_with_false_value(self):
        """Test filter_own_tasks when value is False"""
        from task_manager.tasks.filters import TaskFilter
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/')
        request.user = self.user
        
        filter_instance = TaskFilter(queryset=Task.objects.all())
        filter_instance.request = request
        
        # Test with False value
        queryset = Task.objects.all()
        result = filter_instance.filter_own_tasks(queryset, 'author', False)
        
        # Should return original queryset when value is False
        self.assertEqual(result, queryset)

    def test_filter_own_tasks_with_none_value(self):
        """Test filter_own_tasks when value is None"""
        from task_manager.tasks.filters import TaskFilter
        from django.test import RequestFactory
        
        factory = RequestFactory()
        request = factory.get('/')
        request.user = self.user
        
        filter_instance = TaskFilter(queryset=Task.objects.all())
        filter_instance.request = request
        
        # Test with None value
        queryset = Task.objects.all()
        result = filter_instance.filter_own_tasks(queryset, 'author', None)
        
        # Should return original queryset when value is None
        self.assertEqual(result, queryset)

    # def test_get_base_queryset_without_team(self):
    #     """Test _get_base_queryset when no team is available"""
    #     from task_manager.tasks.filters import TaskFilter
    #     from django.test import RequestFactory
        
    #     factory = RequestFactory()
    #     request = factory.get('/')
    #     request.user = self.user
    #     # No active_team set
        
    #     filter_instance = TaskFilter(queryset=Task.objects.all())
    #     filter_instance.request = request
        
    #     # Test getting base queryset without team
    #     queryset = filter_instance._get_base_queryset()
        
    #     # Should return tasks filtered by author and no team
    #     self.assertTrue(queryset.filter(author=self.user, team__isnull=True).exists())
