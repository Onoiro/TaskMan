from django.utils.deprecation import MiddlewareMixin
from task_manager.teams.models import Team


class ActiveTeamMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if not request.user.is_authenticated:
            request.active_team = None
            return

        # get active team uuid from session
        active_team_uuid = request.session.get('active_team_uuid')

        if active_team_uuid:
            try:
                # check if user is a member of this team
                # use .get() to raise DoesNotExist if not found
                team = Team.objects.get(
                    uuid=active_team_uuid,
                    memberships__user=request.user
                )
                request.active_team = team
            except Team.DoesNotExist:
                request.active_team = None
                # clear invalid session data
                if 'active_team_uuid' in request.session:
                    del request.session['active_team_uuid']
        else:
            request.active_team = None
