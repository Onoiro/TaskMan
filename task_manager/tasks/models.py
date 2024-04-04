from django.db import models
from django.contrib.auth.models import User
from task_manager.statuses.models import Status
from django.utils.translation import gettext_lazy as _


class Task(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(
        max_length=150,
        unique=True,
        blank=False,
        verbose_name=_('Name')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )
    status = models.ForeignKey(
        Status,
        on_delete=models.PROTECT,
        verbose_name=_('Status'),
    )
    executor = models.ForeignKey(
        User,
        related_name='executor_set',
        on_delete=models.PROTECT,
        verbose_name=_('Executor'),
    )
    author = models.ForeignKey(
        User,
        related_name='author_set',
        on_delete=models.PROTECT,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at')
    )
