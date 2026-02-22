import uuid

from django.db import models
from task_manager.user.models import User
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinLengthValidator


class Team(models.Model):
    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

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
        through_fields=('team', 'user'),
        related_name='member_teams'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at')
    )

    def get_admins(self):
        return User.objects.filter(
            team_memberships__team=self,
            team_memberships__role='admin'
        )

    def is_admin(self, user):
        return TeamMembership.objects.filter(
            team=self,
            user=user,
            role='admin'
        ).exists()

    def is_member(self, user):
        return TeamMembership.objects.filter(
            team=self,
            user=user
        ).exists()

    def __str__(self):
        return self.name


class TeamMembership(models.Model):
    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True
    )
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
