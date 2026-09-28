from django import forms
from django.utils.translation import gettext_lazy as _

from task_manager.limit_service import LimitService
from task_manager.notes.models import Note
from task_manager.notes.validators import validate_image_upload
from task_manager.tasks.models import Task


class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ['title', 'content', 'task']

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if self.request is None or not self.request.user.is_authenticated:
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
        self.fields['task'].help_text = _("Optional")

    def clean(self):
        cleaned_data = super().clean()

        content = (cleaned_data.get('content') or '').strip()
        if content:
            return cleaned_data

        error = self._get_textless_note_error()
        if error is not None:
            raise forms.ValidationError(error)

        return cleaned_data

    def _get_textless_note_error(self):
        """Return an error message when the textless note cannot be saved.

        Text is optional only while the note keeps an image, so the files
        have to pass both the format check and the plan limit.
        """
        if self.instance.pk and self.instance.images.exists():
            return None

        uploaded_files = self.files.getlist('images')
        if not uploaded_files:
            return _("Add some text or attach at least one image.")

        for uploaded_file in uploaded_files:
            error = validate_image_upload(uploaded_file)
            if error is not None:
                # Report the file problem instead of the missing text
                return error

        return self._get_image_limit_error(len(uploaded_files))

    def _get_image_limit_error(self, valid_count):
        """Return the plan limit message when the files do not fit."""
        if self.request is None or not self.request.user.is_authenticated:
            return None

        service = LimitService(self.request.user)
        result = service.can_add_note_images(self.instance, valid_count)
        if not result.allowed:
            return result.message
        return None

    def clean_task(self):
        task = self.cleaned_data.get('task')
        if (not task
                or not self.request
                or not self.request.user.is_authenticated):
            return task

        user = self.request.user
        team = getattr(self.request, 'active_team', None)

        # Validate task belongs to user's context
        error_message = self._validate_task_context(task, user, team)
        if error_message is not None:
            raise forms.ValidationError(error_message)

        return task

    def _validate_task_context(self, task, user, team):
        """Validate task context and return error message or None if valid."""
        if team:
            # Team context: task must belong to same team
            if task.team != team:
                return _("Task must be from the same team.")
        else:
            # Individual context: task must be personal
            if task.team is not None:
                return _("Cannot attach note to team task in individual mode.")
            if task.author != user:
                return _("You can only attach notes to your own tasks.")
        return None
