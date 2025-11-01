from django.utils.deprecation import MiddlewareMixin
from task_manager.teams.models import Team


class ActiveTeamMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.user.is_authenticated:
            # Получаем ID активной команды из сессии
            active_team_id = request.session.get('active_team_id')

            if active_team_id:
                try:
                    # Проверяем, что пользователь состоит в этой команде
                    team = Team.objects.filter(
                        id=active_team_id,
                        memberships__user=request.user
                    ).first()
                    request.active_team = team
                except Team.DoesNotExist:
                    request.active_team = None
                    del request.session['active_team_id']
            else:
                request.active_team = None
        else:
            request.active_team = None
