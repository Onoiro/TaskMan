from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from task_manager.notifications.models import Notification
from task_manager.user.models import User


def _create(recipient, notification_type, message, action_url=''):
    """
    Private helper to create a notification.
    All public functions use this to avoid code duplication.
    """
    Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        message=message,
        action_url=action_url,
    )


def notify_task_assigned(task, assignee, actor):
    """
    Notify user when assigned to a task.
    Skip if user assigned themselves.
    """
    if assignee == actor:
        return

    action_url = reverse('tasks:tasks-list')
    message = _(
        f"You have been assigned to task: {task.name}"
    )
    _create(
        recipient=assignee,
        notification_type=Notification.NotificationType.TASK_ASSIGNED,
        message=message,
        action_url=action_url,
    )


def notify_task_unassigned(task, assignee, actor):
    """
    Notify user when removed from task executors.
    Skip if user removed themselves.
    """
    if assignee == actor:
        return

    action_url = reverse('tasks:tasks-list')
    message = _(
        f"You have been removed from task: {task.name}"
    )
    _create(
        recipient=assignee,
        notification_type=Notification.NotificationType.TASK_UNASSIGNED,
        message=message,
        action_url=action_url,
    )


def notify_task_status_changed(task, actor):
    """
    Notify task author when status changes.
    Skip if author changed the status themselves.
    """
    if task.author == actor:
        return

    action_url = reverse('tasks:tasks-list')
    message = _(
        f"Status of task '{task.name}' has been changed"
    )
    _create(
        recipient=task.author,
        notification_type=Notification.NotificationType.TASK_STATUS_CHANGED,
        message=message,
        action_url=action_url,
    )


def notify_task_completed(task, actor):
    """
    Notify task author when task is completed.
    Skip if author completed the task themselves.
    """
    if task.author == actor:
        return

    action_url = reverse('tasks:tasks-list')
    message = _(
        f"Task '{task.name}' has been completed"
    )
    _create(
        recipient=task.author,
        notification_type=Notification.NotificationType.TASK_COMPLETED,
        message=message,
        action_url=action_url,
    )


def notify_team_join_request(team, applicant):
    """
    Notify all team admins about a join request.
    """
    action_url = reverse('teams:team-detail', kwargs={'uuid': team.uuid})
    message = _(
        f"{applicant.username} wants to join team '{team.name}'"
    )

    admins = User.objects.filter(
        team_memberships__team=team,
        team_memberships__role='admin',
        team_memberships__status='active',
    )

    for admin in admins:
        _create(
            recipient=admin,
            notification_type=Notification.NotificationType.TEAM_JOIN_REQUEST,
            message=message,
            action_url=action_url,
        )


def notify_team_member_joined(team, new_member):
    """
    Notify all team admins about a new member joining.
    Skip if the new member is an admin themselves.
    """
    # Check if new_member is an admin
    is_admin = team.memberships.filter(
        user=new_member,
        role='admin',
        status='active',
    ).exists()

    if is_admin:
        return

    action_url = reverse('teams:team-detail', kwargs={'uuid': team.uuid})
    message = _(
        f"{new_member.username} has joined team '{team.name}'"
    )

    admins = User.objects.filter(
        team_memberships__team=team,
        team_memberships__role='admin',
        team_memberships__status='active',
    )

    for admin in admins:
        _create(
            recipient=admin,
            notification_type=Notification.NotificationType.TEAM_MEMBER_JOINED,
            message=message,
            action_url=action_url,
        )


def notify_request_approved(team, user):
    """
    Notify user when their join request is approved.
    """
    action_url = reverse('teams:team-detail', kwargs={'uuid': team.uuid})
    message = _(
        f"Your request to join team '{team.name}' has been approved"
    )
    _create(
        recipient=user,
        notification_type=Notification.NotificationType.TEAM_REQUEST_APPROVED,
        message=message,
        action_url=action_url,
    )


def notify_request_rejected(team, user):
    """
    Notify user when their join request is rejected.
    """
    action_url = reverse('teams:team-detail', kwargs={'uuid': team.uuid})
    message = _(
        f"Your request to join team '{team.name}' has been rejected"
    )
    _create(
        recipient=user,
        notification_type=Notification.NotificationType.TEAM_REQUEST_REJECTED,
        message=message,
        action_url=action_url,
    )


def notify_member_removed(team, removed_user, actor):
    """
    Notify user when removed from team.
    Skip if user left voluntarily (removed themselves).
    """
    if removed_user == actor:
        return

    action_url = reverse('teams:team-detail', kwargs={'uuid': team.uuid})
    message = _(
        f"You have been removed from team '{team.name}'"
    )
    _create(
        recipient=removed_user,
        notification_type=Notification.NotificationType.TEAM_MEMBER_REMOVED,
        message=message,
        action_url=action_url,
    )


def notify_role_changed(team, user, new_role):
    """
    Notify user when their role in team changes.
    """
    action_url = reverse('teams:team-detail', kwargs={'uuid': team.uuid})
    message = _(
        f"Your role in team '{team.name}' has been changed to {new_role}"
    )
    _create(
        recipient=user,
        notification_type=Notification.NotificationType.TEAM_ROLE_CHANGED,
        message=message,
        action_url=action_url,
    )


def notify_team_invited(team, invited_user):
    """
    Notify user when invited to team.
    """
    action_url = reverse('teams:team-detail', kwargs={'uuid': team.uuid})
    message = _(
        f"You have been invited to join team '{team.name}'"
    )
    _create(
        recipient=invited_user,
        notification_type=Notification.NotificationType.TEAM_INVITED,
        message=message,
        action_url=action_url,
    )


def notify_team_deleted(team, members):
    """
    Notify all team members when team is deleted.
    members should be a queryset or list of User objects.
    """
    action_url = reverse('teams:team-join')
    message = _(
        f"Team '{team.name}' has been deleted"
    )

    # Ensure we have a list/queryset to iterate
    if hasattr(members, 'all'):
        members_list = members.all()
    else:
        members_list = members

    for member in members_list:
        _create(
            recipient=member,
            notification_type=Notification.NotificationType.TEAM_DELETED,
            message=message,
            action_url=action_url,
        )