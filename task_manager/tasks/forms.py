from task_manager.tasks.models import Task
from task_manager.user.models import User
from task_manager.statuses.models import Status
from task_manager.labels.models import Label
from django import forms
from django.utils import timezone


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            'name',
            'description',
            'status',
            'executors',
            'labels',
            'deadline',
        ]

    def __init__(self, *args, **kwargs):
        # The request object is added to the form
        # via the get_form_kwargs() method in the view.
        # This is necessary to filter the form fields
        # depending on the user and their team.
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['deadline'].required = False
        # datetime-local requires ISO format (T separator, no localized
        # formats), otherwise the browser silently drops the initial
        # value and saving the form clears the deadline.
        self.fields['deadline'].input_formats = (
            '%Y-%m-%dT%H:%M',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%Y-%m-%d %H:%M:%S',
        )
        self.fields['deadline'].widget = forms.DateTimeInput(
            attrs={'type': 'datetime-local'},
            format='%Y-%m-%dT%H:%M',
        )
        if self.request is None:
            return

        user = self.request.user

        # Protection against anonymous users
        if not user.is_authenticated:
            return

        team = getattr(self.request, 'active_team', None)

        if team:
            # team mode - only active members can be executors
            self.fields['executors'].queryset = User.objects.filter(
                team_memberships__team=team,
                team_memberships__status='active'
            )
            self.fields['status'].queryset = Status.objects.filter(
                team=team
            )
            self.fields['labels'].queryset = Label.objects.filter(
                team=team
            )
            # default status is the first one (e.g. "New")
            self.fields['status'].initial = (
                self.fields['status'].queryset.first()
            )
            # if team has only one member - set executor to author
            if team.memberships.count() == 1:
                self.fields['executors'].initial = [user]
        else:
            # individual mode
            self.fields['executors'].queryset = User.objects.filter(
                pk=user.pk
            )
            self.fields['status'].queryset = Status.objects.filter(
                creator=user,
                team__isnull=True
            )
            self.fields['labels'].queryset = Label.objects.filter(
                creator=user,
                team__isnull=True
            )
            # default status is the first one (e.g. "New")
            self.fields['status'].initial = (
                self.fields['status'].queryset.first()
            )
            # user is executor in individual mode
            self.fields['executors'].initial = [user]
            self.fields['executors'].widget.attrs['readonly'] = True

    def clean_deadline(self):
        deadline = self.cleaned_data.get('deadline')
        if deadline and timezone.is_naive(deadline):
            # datetime-local submits naive time in user's local zone
            deadline = timezone.make_aware(
                deadline,
                timezone.get_current_timezone()
            )
        return deadline
