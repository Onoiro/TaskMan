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

    executors = django_filters.ModelChoiceFilter(
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
        label=_('After'),
        lookup_expr='gte',
        widget=forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control'}
        ),
        label_suffix="",
    )

    created_before = django_filters.DateFilter(
        field_name='created_at',
        label=_('Before'),
        lookup_expr='lte',
        widget=forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control'}
        ),
        label_suffix="",
    )

    class Meta:
        model = Task
        fields = [
            'status', 'executors', 'labels', 'self_tasks',
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

            self.filters['executors'].queryset = team_users
            self.filters['status'].queryset = Status.objects.filter(team=team)
            self.filters['labels'].queryset = Label.objects.filter(team=team)
        else:
            self.filters['executors'].queryset = User.objects.filter(pk=user.pk)
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

    def _is_excluded(self, param_name):
        """Check if exclude checkbox is checked."""
        data = self.form.data if self.form.is_bound else self.form.initial
        valid_values = ('on', 'true', '1', 'checked')
        return param_name in data and data[param_name] in valid_values

    def _get_filter_value(self, field_name):
        """Get filter value from cleaned_data or initial."""
        if self.form.is_valid():
            value = self.form.cleaned_data.get(field_name)
            if value is not None:
                # Handle list of User objects for ManyToMany fields
                if isinstance(value, (list, tuple)) and value:
                    first = value[0]
                    if hasattr(first, 'pk'):
                        return [item.pk for item in value]
                # Handle single User object
                if hasattr(value, 'pk'):
                    return value.pk
                return value
        return self.form.initial.get(field_name)

    def _get_base_queryset(self):
        """Get base queryset based on team context."""
        user = self.request.user
        team = getattr(self.request, 'active_team', None)

        if team:
            return Task.objects.filter(team=team).order_by('-created_at')
        return Task.objects.filter(
            author=user, team__isnull=True
        ).order_by('-created_at')

    def _apply_model_filter(self, qs, field_name, lookup_field=None):
        """Apply filter with optional exclude mode."""
        value = self._get_filter_value(field_name)
        if not value:
            return qs

        lookup_field = lookup_field or field_name
        exclude_mode = self._is_excluded(f'{field_name}_exclude')

        # Handle list of IDs for ManyToMany fields
        if isinstance(value, (list, tuple)):
            condition = Q(**{f'{lookup_field}__in': value})
        else:
            condition = Q(**{lookup_field: value})
        return qs.filter(~condition if exclude_mode else condition)

    def _apply_date_filters(self, qs):
        """Apply date range filters."""
        created_after = self._get_filter_value('created_after')
        created_before = self._get_filter_value('created_before')

        if created_after:
            qs = qs.filter(created_at__gte=created_after)
        if created_before:
            qs = qs.filter(created_at__lte=created_before)

        return qs

    def _apply_self_tasks_filter(self, qs):
        """Apply self_tasks filter with exclude support."""
        self_tasks = self._get_filter_value('self_tasks')
        if not self_tasks:
            return qs

        user = self.request.user
        exclude_mode = self._is_excluded('self_tasks_exclude')

        condition = Q(author=user)
        return qs.filter(~condition if exclude_mode else condition)

    def filter_queryset(self, queryset):
        """Override to handle exclude logic properly."""
        qs = self._get_base_queryset()

        # Apply model choice filters
        qs = self._apply_model_filter(qs, 'status')
        qs = self._apply_model_filter(qs, 'executors')
        qs = self._apply_model_filter(qs, 'labels')

        # Apply special filters
        qs = self._apply_self_tasks_filter(qs)
        qs = self._apply_date_filters(qs)

        return qs
