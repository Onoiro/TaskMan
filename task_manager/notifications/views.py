from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from task_manager.notifications.models import Notification


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
