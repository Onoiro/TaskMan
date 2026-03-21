from django import forms
from django.utils.translation import gettext_lazy as _

from task_manager.notes.models import Note
from task_manager.tasks.models import Task


class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ['title', 'content', 'task']

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if self.request is None:
            return

        user = self.request.user
        team = getattr(self.request, 'active_team', None)

        # Filter tasks based on context (team or individual)
        if team:
            self.fields['task'].queryset = Task.objects.filter(team=team)
        else:
            self.fields['task'].queryset = Task.objects.filter(
                author=user,
                team__isnull=True
            )

        # Make task field not required
        self.fields['task'].required = False

    def clean_task(self):
        task = self.cleaned_data.get('task')
        if not task:
            return task

        # Validate task belongs to user's context
        user = self.request.user
        team = getattr(self.request, 'active_team', None)

        if team:
            # Team context: task must belong to same team
            if task.team != team:
                raise forms.ValidationError(
                    _("Task must be from the same team.")
                )
        else:
            # Individual context: task must be personal
            if task.team is not None:
                raise forms.ValidationError(
                    _("Cannot attach note to team task in individual mode.")
                )
            if task.author != user:
                raise forms.ValidationError(
                    _("You can only attach notes to your own tasks.")
                )

        return task
