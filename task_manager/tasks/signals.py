from django.db.models.signals import m2m_changed, pre_save, post_save
from django.dispatch import receiver

from task_manager.tasks.models import Task
from task_manager.notifications.services import (
    notify_task_assigned,
    notify_task_unassigned,
    notify_task_status_changed,
    notify_task_completed,
)


def _notify_assigned(instance, pk_set, actor):
    """Notify users added as task executors."""
    from task_manager.user.models import User
    for user_pk in pk_set:
        try:
            user = User.objects.get(pk=user_pk)
            notify_task_assigned(instance, user, actor)
        except User.DoesNotExist:
            pass


def _notify_unassigned(instance, pk_set, actor):
    """Notify users removed from task executors."""
    from task_manager.user.models import User
    for user_pk in pk_set:
        try:
            user = User.objects.get(pk=user_pk)
            notify_task_unassigned(instance, user, actor)
        except User.DoesNotExist:
            pass


@receiver(m2m_changed, sender=Task.executors.through)
def task_executors_changed(sender, instance, action, pk_set, **kwargs):
    """
    Handle assignment/unassignment of task executors.
    Actor is expected to be set on instance._actor by the view.
    """
    if not isinstance(instance, Task):
        return

    actor = getattr(instance, '_actor', None)
    if actor is None:
        return

    if action == 'post_add':
        _notify_assigned(instance, pk_set, actor)
    elif action == 'post_remove':
        _notify_unassigned(instance, pk_set, actor)


@receiver(pre_save, sender=Task)
def task_pre_save(sender, instance, **kwargs):
    """
    Store old status ID to detect changes in post_save.
    """
    if instance.pk:
        try:
            old = Task.objects.get(pk=instance.pk)
            instance._old_status_id = old.status_id
        except Task.DoesNotExist:
            instance._old_status_id = None
    else:
        instance._old_status_id = None


@receiver(post_save, sender=Task)
def task_post_save(sender, instance, created, **kwargs):
    """
    Notify author and executors about status changes and completion.
    """
    if created:
        return

    actor = getattr(instance, '_actor', None)
    if actor is None:
        return

    old_status_id = getattr(instance, '_old_status_id', None)
    if old_status_id is None or old_status_id == instance.status_id:
        return

    notify_task_status_changed(instance, actor)

    # Notify about completion when status name is "Completed".
    # This relies on the default status name; adding an is_final
    # flag to Status would make it more robust.
    if instance.status.name == 'Completed':
        notify_task_completed(instance, actor)
