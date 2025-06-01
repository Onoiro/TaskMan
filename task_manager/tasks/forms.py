from task_manager.tasks.models import Task
from task_manager.user.models import User
from task_manager.statuses.models import Status
from task_manager.labels.models import Label
from django import forms


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = [
            'name',
            'description',
            'status',
            'executor',
            'labels',
        ]

    def __init__(self, *args, **kwargs):
        # The request object is added to the form
        # via the get_form_kwargs() method in the view.
        # This is necessary to filter the form fields
        # depending on the user and their team.
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        if self.request is None:
            return

        user = self.request.user
        team = user.team

        if team is not None:
            self.fields['executor'].queryset = (
                User.objects.filter(team=team)
            )
            self.fields['status'].queryset = (
                Status.objects.filter(creator__team=team)
            )
            self.fields['labels'].queryset = (
                Label.objects.filter(creator__team=team)
            )
        else:
            self.fields['executor'].queryset = (
                User.objects.filter(pk=user.pk)
            )
            self.fields['status'].queryset = (
                Status.objects.filter(creator=user)
            )
            self.fields['labels'].queryset = (
                Label.objects.filter(creator=user)
            )
