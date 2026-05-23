from django.db import models
from django.utils.translation import gettext_lazy as _

from task_manager.user.models import User


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        TASK_ASSIGNED = 'task_assigned', _('Task assigned')
        TASK_UNASSIGNED = 'task_unassigned', _('Task unassigned')
        TASK_STATUS_CHANGED = (
            'task_status_changed', _('Task status changed')
        )
        TASK_COMPLETED = 'task_completed', _('Task completed')
        TEAM_JOIN_REQUEST = (
            'team_join_request', _('Team join request')
        )
        TEAM_MEMBER_JOINED = (
            'team_member_joined', _('Team member joined')
        )
        TEAM_REQUEST_APPROVED = (
            'team_request_approved', _('Team request approved')
        )
        TEAM_REQUEST_REJECTED = (
            'team_request_rejected', _('Team request rejected')
        )
        TEAM_MEMBER_REMOVED = (
            'team_member_removed', _('Team member removed')
        )
        TEAM_ROLE_CHANGED = (
            'team_role_changed', _('Team role changed')
        )
        TEAM_INVITED = 'team_invited', _('Team invited')
        TEAM_DELETED = 'team_deleted', _('Team deleted')

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('Recipient')
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        verbose_name=_('Notification type')
    )
    message = models.TextField(
        verbose_name=_('Message')
    )
    action_url = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_('Action URL')
    )
    is_read = models.BooleanField(
        default=False,
        verbose_name=_('Is read')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at')
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(
                fields=['recipient', 'is_read', 'created_at'],
                name='notif_recip_read_created_idx'
            ),
        ]
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')

    def mark_as_read(self):
        """
        Mark notification as read using update_fields
        to avoid unnecessary DB writes.
        """
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=['is_read'])

    def __str__(self):
        return (
            f"{self.notification_type} - {self.recipient.username}"
        )