from task_manager.notifications.models import Notification


def notifications_context(request):
    """
    Provides unread notifications and count for the authenticated user.
    """
    if not request.user.is_authenticated:
        return {}

    unread_notifications = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).order_by('-created_at')[:10]

    return {
        'unread_notifications': unread_notifications,
        'unread_notifications_count': len(unread_notifications),
    }
