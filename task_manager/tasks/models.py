from django.db import models
from task_manager.user.models import User
from task_manager.teams.models import Team
from task_manager.statuses.models import Status
from task_manager.labels.models import Label
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _


class Task(models.Model):
    id = models.AutoField(primary_key=True)
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
    labels = models.ManyToManyField(
        Label,
        blank=True,
        verbose_name=_('Labels'),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at')
    )

    def save(self, *args, **kwargs):
        # Автоматически определяем команду, если не указана
        if not self.team and self.author:
            # Если задача создается без команды, это индивидуальная задача
            pass
        super().save(*args, **kwargs)
