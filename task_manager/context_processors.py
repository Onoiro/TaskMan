from django.conf import settings
from task_manager.teams.models import TeamMembership


def team_context(request):
    context = {'VERSION': settings.VERSION}
    if request.user.is_authenticated:
        # Get only active team memberships
        user_teams = TeamMembership.objects.filter(
            user=request.user,
            status='active'
        ).select_related('team')

        context['user_teams'] = user_teams
        context['active_team'] = getattr(request, 'active_team', None)

        # define if user work with team or individual
        context['is_team_mode'] = bool(context['active_team'])

    return context
