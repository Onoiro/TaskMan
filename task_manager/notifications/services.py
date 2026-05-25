from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from task_manager.notifications.models import Notification
from task_manager.user.models import User


def _create(recipient, notification_type, message_key='', message_params=None,
            message='', action_url=''):
    """
    Private helper to create a notification.
    All public functions use this to avoid code duplication.

    Args:
        recipient: User who receives the notification
        notification_type: Type from NotificationType
        message_key: Translation key for the message template
        message_params: Dict of parameters for template formatting
        message: Legacy field for backward compatibility
        action_url: URL for the notification action
    """
    Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        message=message,
        message_key=message_key,
        message_params=message_params or {},
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
    _create(
        recipient=assignee,
        notification_type=Notification.NotificationType.TASK_ASSIGNED,
        message_key='You have been assigned to task: {task_name}',
        message_params={'task_name': task.name},
        message=_('You have been assigned to task: {task_name}').format(
            task_name=task.name
        ),
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
    _create(
        recipient=assignee,
        notification_type=Notification.NotificationType.TASK_UNASSIGNED,
        message_key='You have been removed from task: {task_name}',
        message_params={'task_name': task.name},
        message=_('You have been removed from task: {task_name}').format(
            task_name=task.name
        ),
        action_url=action_url,
    )


def notify_task_status_changed(task, actor):
    """
    Notify task author and executors about status change.
    Skip the actor to avoid self-notifications.
    """
    action_url = reverse('tasks:tasks-list')
    message_params = {'task_name': task.name}
    message = _('Status of task \'{task_name}\' has been changed').format(
        **message_params
    )

    # Collect unique recipients to prevent duplicate notifications
    # when the author is also an executor.
    recipients = set()
    if task.author:
        recipients.add(task.author)
    for executor in task.executors.all():
        recipients.add(executor)

    for recipient in recipients:
        if recipient == actor:
            continue
        _create(
            recipient=recipient,
            notification_type=Notification.NotificationType.TASK_STATUS_CHANGED,
            message_key='Status of task \'{task_name}\' has been changed',
            message_params=message_params,
            message=message,
            action_url=action_url,
        )


def notify_task_completed(task, actor):
    """
    Notify task author and executors about task completion.
    Skip the actor to avoid self-notifications.
    """
    action_url = reverse('tasks:tasks-list')
    message_params = {'task_name': task.name}
    message = _('Task \'{task_name}\' has been completed').format(
        **message_params
    )

    recipients = set()
    if task.author:
        recipients.add(task.author)
    for executor in task.executors.all():
        recipients.add(executor)

    for recipient in recipients:
        if recipient == actor:
            continue
        _create(
            recipient=recipient,
            notification_type=Notification.NotificationType.TASK_COMPLETED,
            message_key='Task \'{task_name}\' has been completed',
            message_params=message_params,
            message=message,
            action_url=action_url,
        )


def notify_team_join_request(team, applicant):
    """
    Notify all team admins about a join request.
    """
    action_url = reverse('teams:team-detail', kwargs={'uuid': team.uuid})
    message_params = {
        'username': applicant.username,
        'team_name': team.name,
    }
    message = _(
        '{username} wants to join team \'{team_name}\''
    ).format(**message_params)

    admins = User.objects.filter(
        team_memberships__team=team,
        team_memberships__role='admin',
        team_memberships__status='active',
    )

    for admin in admins:
        _create(
            recipient=admin,
            notification_type=Notification.NotificationType.TEAM_JOIN_REQUEST,
            message_key='{username} wants to join team \'{team_name}\'',
            message_params=message_params,
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
    message_params = {
        'username': new_member.username,
        'team_name': team.name,
    }
    message = _(
        '{username} has joined team \'{team_name}\''
    ).format(**message_params)

    admins = User.objects.filter(
        team_memberships__team=team,
        team_memberships__role='admin',
        team_memberships__status='active',
    )

    for admin in admins:
        _create(
            recipient=admin,
            notification_type=Notification.NotificationType.TEAM_MEMBER_JOINED,
            message_key='{username} has joined team \'{team_name}\'',
            message_params=message_params,
            message=message,
            action_url=action_url,
        )


def notify_request_approved(team, user):
    """
    Notify user when their join request is approved.
    """
    action_url = reverse('teams:team-detail', kwargs={'uuid': team.uuid})
    message_params = {'team_name': team.name}
    message = _(
        'Your request to join team \'{team_name}\' has been approved'
    ).format(**message_params)
    _create(
        recipient=user,
        notification_type=Notification.NotificationType.TEAM_REQUEST_APPROVED,
        message_key=(
            'Your request to join team \'{team_name}\' has been approved'
        ),
        message_params=message_params,
        message=message,
        action_url=action_url,
    )


def notify_request_rejected(team, user):
    """
    Notify user when their join request is rejected.
    """
    action_url = reverse('teams:team-detail', kwargs={'uuid': team.uuid})
    message_params = {'team_name': team.name}
    message = _(
        'Your request to join team \'{team_name}\' has been rejected'
    ).format(**message_params)
    _create(
        recipient=user,
        notification_type=Notification.NotificationType.TEAM_REQUEST_REJECTED,
        message_key=(
            'Your request to join team \'{team_name}\' has been rejected'
        ),
        message_params=message_params,
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
    message_params = {'team_name': team.name}
    message = _(
        'You have been removed from team \'{team_name}\''
    ).format(**message_params)
    _create(
        recipient=removed_user,
        notification_type=Notification.NotificationType.TEAM_MEMBER_REMOVED,
        message_key='You have been removed from team \'{team_name}\'',
        message_params=message_params,
        message=message,
        action_url=action_url,
    )


def notify_role_changed(team, user, new_role):
    """
    Notify user when their role in team changes.
    """
    action_url = reverse('teams:team-detail', kwargs={'uuid': team.uuid})
    message_params = {'team_name': team.name, 'role': new_role}
    message = _(
        'Your role in team \'{team_name}\' has been changed to {role}'
    ).format(**message_params)
    _create(
        recipient=user,
        notification_type=Notification.NotificationType.TEAM_ROLE_CHANGED,
        message_key=(
            'Your role in team \'{team_name}\' has been changed to {role}'
        ),
        message_params=message_params,
        message=message,
        action_url=action_url,
    )


def notify_team_invited(team, invited_user):
    """
    Notify user when invited to team.
    """
    action_url = reverse('teams:team-detail', kwargs={'uuid': team.uuid})
    message_params = {'team_name': team.name}
    message = _(
        'You have been invited to join team \'{team_name}\''
    ).format(**message_params)
    _create(
        recipient=invited_user,
        notification_type=Notification.NotificationType.TEAM_INVITED,
        message_key='You have been invited to join team \'{team_name}\'',
        message_params=message_params,
        message=message,
        action_url=action_url,
    )


def notify_team_deleted(team, members):
    """
    Notify all team members when team is deleted.
    members should be a queryset or list of User objects.
    """
    action_url = reverse('teams:team-join')
    message_params = {'team_name': team.name}
    message = _(
        'Team \'{team_name}\' has been deleted'
    ).format(**message_params)

    # Ensure we have a list/queryset to iterate
    if hasattr(members, 'all'):
        members_list = members.all()
    else:
        members_list = members

    for member in members_list:
        _create(
            recipient=member,
            notification_type=Notification.NotificationType.TEAM_DELETED,
            message_key='Team \'{team_name}\' has been deleted',
            message_params=message_params,
            message=message,
            action_url=action_url,
        )
