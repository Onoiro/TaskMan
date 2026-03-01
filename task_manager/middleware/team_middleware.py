from django.utils.deprecation import MiddlewareMixin
from task_manager.teams.models import TeamMembership


class ActiveTeamMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if not request.user.is_authenticated:
            request.active_team = None
            return

        # get active team uuid from session
        active_team_uuid = request.session.get('active_team_uuid')

        if active_team_uuid:
            try:
                # check if user is an active member of this team
                membership = TeamMembership.objects.get(
                    team__uuid=active_team_uuid,
                    user=request.user,
                    status='active'
                )
                request.active_team = membership.team
            except TeamMembership.DoesNotExist:
                request.active_team = None
                # clear invalid session data
                if 'active_team_uuid' in request.session:
                    del request.session['active_team_uuid']
        else:
            request.active_team = None
