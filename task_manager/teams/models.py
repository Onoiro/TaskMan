from django.db import models
# from django.contrib.auth.models import User
from task_manager.user.models import User
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinLengthValidator


class Team(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(
        max_length=150,
        unique=True,
        blank=False,
        verbose_name=_('Name')
    )
    password = models.CharField(
        max_length=128,
        validators=[MinLengthValidator(3)],
        verbose_name=_('Team password'),
        help_text=_('Minimum length is 3 characters')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )
    team_admin = models.ForeignKey(
        User,
        related_name='team_admin_set',
        on_delete=models.PROTECT,
        verbose_name=_('Team admin'),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at')
    )
