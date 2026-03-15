import django_filters
from django import forms
from django.db.models import Q
from task_manager.tasks.models import Task
from task_manager.statuses.models import Status
from task_manager.labels.models import Label
from task_manager.user.models import User
from django.utils.translation import gettext_lazy as _


class TaskFilter(django_filters.FilterSet):

    search = django_filters.CharFilter(
        method='filter_search',
        label=_('Search'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Task name...'),
            'autocomplete': 'off',
        }),
        label_suffix="",
    )

    status = django_filters.ModelChoiceFilter(
        queryset=Status.objects.all(),
        label=_('Status'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label_suffix="",
    )

    author = django_filters.ModelChoiceFilter(
        queryset=User.objects.all(),
        label=_('Author'),
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

    my_tasks = django_filters.BooleanFilter(
        label=_('My tasks'),
        method='filter_my_tasks',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label_suffix="",
    )

    created_after = django_filters.DateFilter(
        field_name='created_at',
        label=_('From'),
        lookup_expr='gte',
        widget=forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control'}
        ),
        label_suffix="",
    )

    created_before = django_filters.DateFilter(
        field_name='created_at',
        label=_('To'),
        lookup_expr='lte',
        widget=forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control'}
        ),
        label_suffix="",
    )

    has_checklist = django_filters.BooleanFilter(
        label=_('Has checklist'),
        method='filter_has_checklist',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label_suffix="",
    )

    class Meta:
        model = Task
        fields = [
            'search', 'status', 'author', 'executors', 'labels',
            'my_tasks', 'created_after', 'created_before', 'has_checklist',
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
                team_memberships__team=team,
                team_memberships__status='active'
            ).distinct()

            self.filters['executors'].queryset = team_users
            self.filters['author'].queryset = team_users
            self.filters['status'].queryset = Status.objects.filter(team=team)
            self.filters['labels'].queryset = Label.objects.filter(team=team)
        else:
            self.filters['executors'].queryset = User.objects.filter(
                pk=user.pk)
            self.filters['author'].queryset = User.objects.filter(pk=user.pk)
            self.filters['status'].queryset = Status.objects.filter(
                creator=user,
                team__isnull=True
            )
            self.filters['labels'].queryset = Label.objects.filter(
                creator=user,
                team__isnull=True
            )

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(name__icontains=value) | Q(description__icontains=value)
        )

    def filter_my_tasks(self, queryset, name, value):
        """Filter tasks where user is author OR executor."""
        user = self.request.user
        if value:
            return queryset.filter(
                Q(author=user) | Q(executors=user)
            ).distinct()
        return queryset

    def filter_has_checklist(self, queryset, name, value):
        if value:
            return queryset.filter(checklist_items__isnull=False).distinct()
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
                if hasattr(value, 'pk'):
                    return value.pk
                return value
        return self.form.initial.get(field_name)

    def _get_base_queryset(self):
        """Get base queryset based on team context."""
        user = self.request.user
        team = getattr(self.request, 'active_team', None)

        sort = self.request.GET.get('sort', '-updated_at')
        valid_sorts = {
            '-updated_at', 'updated_at',
            '-created_at', 'created_at',
            'name', '-name',
        }
        if sort not in valid_sorts:
            sort = '-updated_at'

        if team:
            return Task.objects.filter(team=team).order_by(sort)
        return Task.objects.filter(
            author=user, team__isnull=True
        ).order_by(sort)

    def _apply_model_filter(self, qs, field_name, lookup_field=None):
        """Apply filter with optional exclude mode."""
        value = self._get_filter_value(field_name)
        if not value:
            return qs

        lookup_field = lookup_field or field_name
        exclude_mode = self._is_excluded(f'{field_name}_exclude')

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

    def _apply_my_tasks_filter(self, qs):
        """Apply my_tasks filter — author OR executor."""
        my_tasks = self._get_filter_value('my_tasks')
        if not my_tasks:
            return qs

        user = self.request.user
        exclude_mode = self._is_excluded('my_tasks_exclude')

        condition = Q(author=user) | Q(executors=user)
        if exclude_mode:
            return qs.exclude(condition).distinct()
        return qs.filter(condition).distinct()

    def _apply_search_filter(self, qs):
        """Apply text search filter."""
        search = self._get_filter_value('search')
        if not search:
            return qs
        return qs.filter(
            Q(name__icontains=search) | Q(description__icontains=search)
        )

    def _apply_has_checklist_filter(self, qs):
        """Apply checklist presence filter."""
        has_checklist = self._get_filter_value('has_checklist')
        if not has_checklist:
            return qs
        return qs.filter(checklist_items__isnull=False).distinct()

    def filter_queryset(self, queryset):
        """Override to handle exclude logic properly."""
        qs = self._get_base_queryset()

        # Text search
        qs = self._apply_search_filter(qs)

        # Model choice filters
        qs = self._apply_model_filter(qs, 'status')
        qs = self._apply_model_filter(qs, 'author')
        qs = self._apply_model_filter(qs, 'executors')
        qs = self._apply_model_filter(qs, 'labels')

        # Special filters
        qs = self._apply_my_tasks_filter(qs)
        qs = self._apply_date_filters(qs)
        qs = self._apply_has_checklist_filter(qs)

        return qs
