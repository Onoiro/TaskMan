from django.db import models
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
    members = models.ManyToManyField(
        'user.User',
        through='TeamMembership',
        through_fields=('team', 'user'),  # явно указываем поля
        related_name='member_teams'
    )
    # team_admin = models.ForeignKey(
    #     User,
    #     related_name='team_admin_set',
    #     on_delete=models.PROTECT,
    #     verbose_name=_('Team admin'),
    # )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at')
    )


def __str__(self):
    return self.name


class TeamMembership(models.Model):
    ROLE_CHOICES = [
        ('admin', _('Admin')),
        ('member', _('Member')),
    ]

    user = models.ForeignKey(
        'user.User',
        on_delete=models.CASCADE,
        related_name='team_memberships'
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='member'
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'team']

    def __str__(self):
        return f"{self.user.username} - {self.team.name} ({self.role})"
