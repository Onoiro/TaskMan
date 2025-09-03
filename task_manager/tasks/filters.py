import django_filters
from django import forms
from task_manager.tasks.models import Task
from task_manager.statuses.models import Status
from task_manager.labels.models import Label
from task_manager.user.models import User
from django.utils.translation import gettext_lazy as _


class TaskFilter(django_filters.FilterSet):

    status = django_filters.ModelChoiceFilter(
        queryset=Status.objects.all(),
        label=_('Status'),
        widget=forms.Select,
        label_suffix="",
    )

    executor = django_filters.ModelChoiceFilter(
        queryset=User.objects.all(),
        label=_('Executor'),
        widget=forms.Select,
        label_suffix="",
    )

    labels = django_filters.ModelChoiceFilter(
        queryset=Label.objects.all(),
        label=_('Label'),
        widget=forms.Select,
        label_suffix="",
    )

    self_tasks = django_filters.BooleanFilter(
        field_name='author',
        label=_('Just my tasks'),
        widget=forms.CheckboxInput(),
        method='filter_own_tasks',
        label_suffix="",
    )

    class Meta:
        model = Task
        fields = ['status', 'executor', 'labels', 'self_tasks']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.request
        if request is None:
            return
        user = request.user
        team = getattr(request, 'active_team', None)

        if team:
            # Фильтруем по команде
            from task_manager.teams.models import TeamMembership
            team_users = User.objects.filter(
                team_memberships__team=team
            ).distinct()
            
            self.filters['executor'].queryset = team_users
            self.filters['status'].queryset = Status.objects.filter(team=team)
            self.filters['labels'].queryset = Label.objects.filter(team=team)
        else:
            # Индивидуальный режим
            self.filters['executor'].queryset = User.objects.filter(pk=user.pk)
            self.filters['status'].queryset = Status.objects.filter(
                creator=user,
                team__isnull=True
            )
            self.filters['labels'].queryset = Label.objects.filter(
                creator=user,
                team__isnull=True
            )

        # if team:
        #     self.filters['executor'].queryset = (
        #         User.objects.filter(team=team)
        #     )
        #     self.filters['status'].queryset = (
        #         Status.objects.filter(creator__team=team)
        #     )
        #     self.filters['labels'].queryset = (
        #         Label.objects.filter(creator__team=team)
        #     )
        # else:
        #     self.filters['executor'].queryset = (
        #         User.objects.filter(pk=user.pk)
        #     )
        #     self.filters['status'].queryset = (
        #         Status.objects.filter(creator=user)
        #     )
        #     self.filters['labels'].queryset = (
        #         Label.objects.filter(creator=user)
        #     )

    def filter_own_tasks(self, queryset, name, value):
        user = self.request.user
        if value:
            return queryset.filter(author=user)
        return queryset
