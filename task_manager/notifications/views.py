from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_GET, require_POST

from task_manager.notifications.models import Notification


@require_GET
@login_required
def unread_count(request):
    """
    Returns the exact number of unread notifications for the current user.
    Used by the PWA app badge (Badging API) to stay in sync.
    """
    count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    return JsonResponse({'unread_count': count})


@require_POST
@login_required
def mark_read(request, pk):
    """
    Marks a single notification as read for the current user.
    Returns JSON for AJAX requests, otherwise redirects.
    """
    notification = get_object_or_404(
        Notification,
        pk=pk,
        recipient=request.user
    )
    notification.mark_as_read()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok'})

    return redirect(notification.action_url or 'tasks:tasks-list')


@require_POST
@login_required
def mark_all_read(request):
    """
    Marks all unread notifications as read for the current user.
    Returns JSON for AJAX requests, otherwise redirects.
    """
    Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).update(is_read=True)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok'})

    return redirect(request.META.get('HTTP_REFERER') or 'tasks:tasks-list')
