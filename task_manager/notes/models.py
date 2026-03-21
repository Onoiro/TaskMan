import uuid

from django.db import models
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
        verbose_name=_('Title')
    )
    content = models.TextField(
        blank=False,
        verbose_name=_('Content')
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
