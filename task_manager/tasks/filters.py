import django_filters
from django import forms
from django.db.models import Q
from task_manager.tasks.models import Task
from task_manager.statuses.models import Status
from task_manager.labels.models import Label
from task_manager.user.models import User
from django.utils.translation import gettext_lazy as _


class TaskFilter(django_filters.FilterSet):

    status = django_filters.ModelChoiceFilter(
        queryset=Status.objects.all(),
        label=_('Status'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label_suffix="",
    )

    executor = django_filters.ModelChoiceFilter(
        queryset=User.objects.all(),
        label=_('Executor'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label_suffix="",
    )

    labels = django_filters.ModelChoiceFilter(
        queryset=Label.objects.all(),
        label=_('Label'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label_suffix="",
    )

    self_tasks = django_filters.BooleanFilter(
        field_name='author',
        label=_('Just my tasks'),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        method='filter_own_tasks',
        label_suffix="",
    )

    created_after = django_filters.DateFilter(
        field_name='created_at',
        label=_('Created after'),
        lookup_expr='gte',
        widget=forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control'}
        ),
        label_suffix="",
    )

    created_before = django_filters.DateFilter(
        field_name='created_at',
        label=_('Created before'),
        lookup_expr='lte',
        widget=forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control'}
        ),
        label_suffix="",
    )

    class Meta:
        model = Task
        fields = [
            'status', 'executor', 'labels', 'self_tasks',
            'created_after', 'created_before'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.request
        if request is None:
            return
        user = request.user
        team = getattr(request, 'active_team', None)

        if team:
            team_users = User.objects.filter(
                team_memberships__team=team
            ).distinct()

            self.filters['executor'].queryset = team_users
            self.filters['status'].queryset = Status.objects.filter(team=team)
            self.filters['labels'].queryset = Label.objects.filter(team=team)
        else:
            self.filters['executor'].queryset = User.objects.filter(pk=user.pk)
            self.filters['status'].queryset = Status.objects.filter(
                creator=user,
                team__isnull=True
            )
            self.filters['labels'].queryset = Label.objects.filter(
                creator=user,
                team__isnull=True
            )

    def filter_own_tasks(self, queryset, name, value):
        user = self.request.user
        if value:
            return queryset.filter(author=user)
        return queryset

    def filter_queryset(self, queryset):
        """Override to handle exclude logic properly."""
        # Get raw data from query params
        data = self.form.data if self.form.is_bound else self.form.initial

        # Helper to check if checkbox is checked
        def is_excluded(param_name):
            valid_values = ('on', 'true', '1', 'checked')
            return param_name in data and data[param_name] in valid_values

        user = self.request.user
        team = getattr(self.request, 'active_team', None)

        # Start with base queryset
        if team:
            qs = Task.objects.filter(team=team).order_by('-created_at')
        else:
            qs = Task.objects.filter(
                author=user, team__isnull=True
            ).order_by('-created_at')

        # Get values from form (cleaned_data if valid, else initial)
        status = None
        if self.form.is_valid():
            status = self.form.cleaned_data.get('status')
        if status is None:
            status = self.form.initial.get('status')

        executor = None
        if self.form.is_valid():
            executor = self.form.cleaned_data.get('executor')
        if executor is None:
            executor = self.form.initial.get('executor')

        labels = None
        if self.form.is_valid():
            labels = self.form.cleaned_data.get('labels')
        if labels is None:
            labels = self.form.initial.get('labels')

        self_tasks = None
        if self.form.is_valid():
            self_tasks = self.form.cleaned_data.get('self_tasks')
        if self_tasks is None:
            self_tasks = self.form.initial.get('self_tasks')

        created_after = None
        if self.form.is_valid():
            created_after = self.form.cleaned_data.get('created_after')
        if created_after is None:
            created_after = self.form.initial.get('created_after')

        created_before = None
        if self.form.is_valid():
            created_before = self.form.cleaned_data.get('created_before')
        if created_before is None:
            created_before = self.form.initial.get('created_before')

        # Apply filters with exclude logic
        exclude_mode = is_excluded('status_exclude')
        if status:
            if exclude_mode:
                qs = qs.filter(~Q(status=status))
            else:
                qs = qs.filter(status=status)

        exclude_mode = is_excluded('executor_exclude')
        if executor:
            if exclude_mode:
                qs = qs.filter(~Q(executor=executor))
            else:
                qs = qs.filter(executor=executor)

        exclude_mode = is_excluded('labels_exclude')
        if labels:
            if exclude_mode:
                qs = qs.filter(~Q(labels=labels))
            else:
                qs = qs.filter(labels=labels)

        exclude_mode = is_excluded('self_tasks_exclude')
        if self_tasks:
            if exclude_mode:
                qs = qs.filter(~Q(author=user))
            else:
                qs = qs.filter(author=user)

        if created_after:
            qs = qs.filter(created_at__gte=created_after)

        if created_before:
            qs = qs.filter(created_at__lte=created_before)

        return qs
