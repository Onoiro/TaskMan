import os
import uuid

from django.db import models
from django.core.validators import RegexValidator, MaxLengthValidator
from django.utils.translation import gettext_lazy as _

from task_manager.user.models import User
from task_manager.teams.models import Team
from task_manager.tasks.models import Task


class Note(models.Model):
    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True
    )
    title = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_('Title'),
        validators=[
            RegexValidator(
                r'^[\w \-:,.!?]+$',
                message=_(
                    "Only letters, numbers, spaces, "
                    "and -_.,!? symbols are allowed. "
                    "Symbols <, >, #, & are not allowed."
                )
            ),
        ],
    )
    content = models.TextField(
        blank=True,
        verbose_name=_('Content'),
        validators=[MaxLengthValidator(20000)]
    )
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='notes',
        verbose_name=_('Author')
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notes',
        verbose_name=_('Team')
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notes',
        verbose_name=_('Task')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated at')
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Note')
        verbose_name_plural = _('Notes')

    def __str__(self):
        if self.title:
            return self.title
        return f"Note {self.id}"


def note_image_upload_to(instance, filename):
    """Store images in a per-note directory named by note uuid."""
    ext = os.path.splitext(filename)[1].lower()
    return f"notes/{instance.note.uuid}/{uuid.uuid4()}{ext}"


class NoteImage(models.Model):
    # Upload limits shared by forms, views and tests
    MAX_IMAGE_SIZE_MB = 5
    ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp']

    id = models.AutoField(primary_key=True)
    note = models.ForeignKey(
        Note,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name=_('Note')
    )
    image = models.ImageField(
        upload_to=note_image_upload_to,
        verbose_name=_('Image')
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Order')
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Uploaded at')
    )

    class Meta:
        ordering = ['order', 'id']
        verbose_name = _('Note image')
        verbose_name_plural = _('Note images')

    def __str__(self):
        return f"Image {self.id} for note {self.note_id}"

    def delete(self, *args, **kwargs):
        # Remove the file from storage along with the DB record
        self.image.delete(save=False)
        return super().delete(*args, **kwargs)


# ---------------------------------------------------------------------------
# NoteFile — generic file attachments (documents, archives, etc.)
# ---------------------------------------------------------------------------


def note_file_upload_to(instance, filename):
    """Store files in a per-note directory named by note uuid."""
    ext = os.path.splitext(filename)[1].lower()
    return f"notes/{instance.note.uuid}/{uuid.uuid4()}{ext}"


class NoteFile(models.Model):
    # Upload limits shared by forms, views and tests
    ALLOWED_EXTENSIONS = {
        # Documents
        'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
        'odt', 'ods', 'odp', 'rtf', 'txt', 'md', 'csv',
        # Archives
        'zip', '7z', 'rar', 'tar', 'gz', 'tgz',
        # E-mail files
        'eml', 'msg',
    }
    MAX_FILE_SIZE_MB = 10

    id = models.AutoField(primary_key=True)
    note = models.ForeignKey(
        Note,
        on_delete=models.CASCADE,
        related_name='files',
        verbose_name=_('Note')
    )
    file = models.FileField(
        upload_to=note_file_upload_to,
        verbose_name=_('File')
    )
    original_name = models.CharField(
        max_length=255,
        verbose_name=_('Original name')
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Order')
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Uploaded at')
    )

    class Meta:
        ordering = ['order', 'id']
        verbose_name = _('Note file')
        verbose_name_plural = _('Note files')

    def __str__(self):
        return f"{self.original_name} for note {self.note_id}"

    def delete(self, *args, **kwargs):
        # Remove the file from storage along with the DB record
        self.file.delete(save=False)
        return super().delete(*args, **kwargs)

    def file_icon(self):
        """Return the Bootstrap Icons class for the file extension."""
        ext = os.path.splitext(self.original_name)[1].lower().lstrip('.')
        icons = {
            'pdf': 'bi-file-earmark-pdf text-danger',
            'doc': 'bi-file-earmark-word text-primary',
            'docx': 'bi-file-earmark-word text-primary',
            'xls': 'bi-file-earmark-excel text-success',
            'xlsx': 'bi-file-earmark-excel text-success',
            'ppt': 'bi-file-earmark-ppt text-warning',
            'pptx': 'bi-file-earmark-ppt text-warning',
            'zip': 'bi-file-earmark-zip text-secondary',
            '7z': 'bi-file-earmark-zip text-secondary',
            'rar': 'bi-file-earmark-zip text-secondary',
            'tar': 'bi-file-earmark-zip text-secondary',
            'gz': 'bi-file-earmark-zip text-secondary',
            'tgz': 'bi-file-earmark-zip text-secondary',
            'txt': 'bi-file-earmark-text text-muted',
            'md': 'bi-file-earmark-text text-muted',
            'csv': 'bi-file-earmark-text text-muted',
            'rtf': 'bi-file-earmark-text text-muted',
            'odt': 'bi-file-earmark-text text-muted',
            'ods': 'bi-file-earmark-text text-muted',
            'odp': 'bi-file-earmark-text text-muted',
            'eml': 'bi-file-earmark-text text-muted',
            'msg': 'bi-file-earmark-text text-muted',
        }
        return icons.get(ext, 'bi-file-earmark text-muted')
