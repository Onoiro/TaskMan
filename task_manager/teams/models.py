import uuid

from django.db import models
from task_manager.user.models import User
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinLengthValidator, MaxLengthValidator


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
        verbose_name=_('Description'),
        validators=[MaxLengthValidator(20000)]
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
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('active', _('Active')),
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
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='active'
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'team']

    def __str__(self):
        return f"{self.user.username} - {self.team.name} ({self.role})"


class TeamInvite(models.Model):
    """Model for team join invitations via link"""
    id = models.AutoField(primary_key=True)
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='invites'
    )
    created_by = models.ForeignKey(
        'user.User',
        on_delete=models.CASCADE,
        related_name='created_invites'
    )
    invite_code = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
        verbose_name=_('Invite code')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at')
    )
    expires_at = models.DateTimeField(
        verbose_name=_('Expires at')
    )
    is_used = models.BooleanField(
        default=False,
        verbose_name=_('Is used')
    )
    used_by = models.ForeignKey(
        'user.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='used_invites',
        verbose_name=_('Used by')
    )
    used_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Used at')
    )
    max_uses = models.IntegerField(
        default=1,
        verbose_name=_('Max uses'),
        help_text=_('Number of times invite can be used')
    )
    use_count = models.IntegerField(
        default=0,
        verbose_name=_('Use count')
    )

    class Meta:
        verbose_name = _('Team invite')
        verbose_name_plural = _('Team invites')
        ordering = ['-created_at']

    def __str__(self):
        status = _('Used') if self.is_used else _('Active')
        return f"{self.team.name} - {status} ({self.created_by.username})"

    def is_valid(self):
        """Check if invite is still valid (not expired and not max uses)"""
        from django.utils import timezone
        now = timezone.now()
        return (
            not self.is_used
            and self.use_count < self.max_uses
            and now <= self.expires_at
        )
