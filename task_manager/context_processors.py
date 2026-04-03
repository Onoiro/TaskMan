import hashlib
import os

from django.conf import settings
from task_manager.teams.models import TeamMembership
from task_manager.limit_service import LimitService
from task_manager.limits import FREE_PLAN


def team_context(request):
    context = {'VERSION': settings.VERSION}
    if request.user.is_authenticated:
        user_teams = TeamMembership.objects.filter(
            user=request.user,
            status='active'
        ).select_related('team')

        context['user_teams'] = user_teams
        context['active_team'] = getattr(request, 'active_team', None)
        context['is_team_mode'] = bool(context['active_team'])

    return context


def static_version(request):
    """
    Генерирует версию на основе staticfiles.json.
    Меняется автоматически при каждом collectstatic.
    """
    manifest_path = os.path.join(settings.STATIC_ROOT, 'staticfiles.json')
    try:
        mtime = os.path.getmtime(manifest_path)
        version = hashlib.md5(str(mtime).encode(),
                              usedforsecurity=False).hexdigest()[:8]
    except OSError:
        version = 'dev'

    return {'STATIC_VERSION': version}


def limits_context(request):
    """
    Provides usage statistics and upgrade hints to all templates.
    """
    if not request.user.is_authenticated:
        return {}

    try:
        service = LimitService(request.user)
        usage = service.get_usage_summary()

        # Calculate percentage for each resource
        for key in usage:
            current = usage[key]['current']
            maximum = usage[key]['max']
            if maximum > 0:
                usage[key]['percent'] = min(100, int(current / maximum * 100))
            else:
                usage[key]['percent'] = 0

        # Check if any resource is >= 80% used
        show_upgrade_hint = any(
            usage[key]['percent'] >= 80
            for key in usage
        )

        return {
            'usage': usage,
            'show_upgrade_hint': show_upgrade_hint,
            'free_plan_limits': FREE_PLAN,
        }
    except Exception:
        return {}
