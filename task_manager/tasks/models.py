import uuid

from django.db import models
from task_manager.user.models import User
from task_manager.teams.models import Team
from task_manager.statuses.models import Status
from task_manager.labels.models import Label
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _


class Task(models.Model):
    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True
    )
    name = models.CharField(
        max_length=150,
        unique=False,
        blank=False,
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
        verbose_name=_('Name')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='tasks',
        verbose_name=_('Team')
    )
    status = models.ForeignKey(
        Status,
        on_delete=models.PROTECT,
        verbose_name=_('Status'),
    )
    executors = models.ManyToManyField(
        User,
        related_name='executor_tasks',
        blank=True,
        verbose_name=_('Executors'),
    )
    author = models.ForeignKey(
        User,
        related_name='author_set',
        on_delete=models.SET_NULL,
        null=True,
    )
    labels = models.ManyToManyField(
        Label,
        blank=True,
        verbose_name=_('Labels'),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        null=True,
        verbose_name=_('Updated at')
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_tasks',
        verbose_name=_('Updated by')
    )

    @property
    def was_edited(self):
        if not self.updated_at or not self.created_at:
            return False
        return (self.updated_at - self.created_at).total_seconds() > 2

    @property
    def checklist_total(self):
        return self.checklist_items.count()

    @property
    def checklist_done(self):
        return self.checklist_items.filter(is_done=True).count()

    @property
    def checklist_progress(self):
        if self.checklist_total == 0:
            return 0
        return int((self.checklist_done / self.checklist_total) * 100)

    @property
    def notes_count(self):
        return self.notes.count()

    def save(self, *args, **kwargs):
        # Auto-detect team if not specified
        if not self.team and self.author:
            # If task is created without team, it's an individual task
            pass
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ChecklistItem(models.Model):
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='checklist_items',
        verbose_name=_('Task')
    )
    text = models.CharField(
        max_length=300,
        verbose_name=_('Text')
    )
    is_done = models.BooleanField(
        default=False,
        verbose_name=_('Done')
    )
    position = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Position')
    )

    class Meta:
        ordering = ['position', 'id']

    def __str__(self):
        return self.text[:50]
