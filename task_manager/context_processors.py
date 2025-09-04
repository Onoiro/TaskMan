# context_processors.py
from task_manager.teams.models import TeamMembership
from task_manager.tasks.models import Task

def team_context(request):
    context = {}
    if request.user.is_authenticated:
        # Используем правильный способ получения команд пользователя
        user_teams = TeamMembership.objects.filter(
            user=request.user
        ).select_related('team')

        context['user_teams'] = user_teams
        context['active_team'] = getattr(request, 'active_team', None)

        # Определяем, работает ли пользователь
        # в режиме команды или индивидуально
        context['is_team_mode'] = bool(context['active_team'])

    return context
