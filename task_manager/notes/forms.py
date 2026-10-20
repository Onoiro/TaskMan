from django import forms
from django.utils.translation import gettext_lazy as _

from task_manager.limit_service import LimitService
from task_manager.notes.models import Note
from task_manager.notes.validators import (
    validate_file_upload,
    validate_image_upload,
)
from task_manager.tasks.models import Task


# Upload inputs of the note form: input name, validator, limit check.
# Templates render these inputs directly, so the form only validates them.
UPLOAD_KINDS = [
    ('images', validate_image_upload, LimitService.can_add_note_images),
    ('attachments', validate_file_upload, LimitService.can_add_note_files),
]


class NoteForm(forms.ModelForm):
    """Note fields.

    Uploads ('images' and 'attachments') are not form fields: templates
    render the inputs and views read them from request.FILES, so the form
    only has to reject a note that would end up completely empty.
    """

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

    def _has_existing_uploads(self):
        """Check whether the saved note already keeps any attachment."""
        if not self.instance.pk:
            return False
        return self.instance.images.exists() or self.instance.files.exists()

    def _get_upload_error(self, files, validate, limit_check):
        """Validate one upload input and check the plan limit for it."""
        for uploaded_file in files:
            error = validate(uploaded_file)
            if error is not None:
                return error

        if self.request is None or not self.request.user.is_authenticated:
            return None

        service = LimitService(self.request.user)
        result = limit_check(service, self.instance, len(files))
        return result.message if not result.allowed else None

    def _get_textless_note_error(self):
        """Return an error message when the textless note cannot be saved.

        Text is optional only while the note keeps an image or a file, so
        uploads have to pass both the format check and the plan limit.
        """
        if self._has_existing_uploads():
            return None

        uploaded_any = False
        for input_name, validate, limit_check in UPLOAD_KINDS:
            files = self.files.getlist(input_name)
            if not files:
                continue
            error = self._get_upload_error(files, validate, limit_check)
            if error is not None:
                return error
            uploaded_any = True

        if not uploaded_any:
            return _("Add some text, attach at least one image or file.")
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
