import hashlib
import os

from django.conf import settings
from task_manager.teams.models import TeamMembership


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
        version = hashlib.md5(str(mtime).encode()).hexdigest()[:8]
    except OSError:
        version = 'dev'

    return {'STATIC_VERSION': version}
