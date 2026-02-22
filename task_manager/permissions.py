from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.shortcuts import redirect


UNAUTHORIZED_MESSAGE = _('You are not authorized! Please login.')
USERS_LIST_URL = 'user:user-list'


class CustomPermissions(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, UNAUTHORIZED_MESSAGE)
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)


class UserPermissions(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if self.request.user != self.get_object():
            messages.error(
                request,
                _("You don't have permissions to modify another user.")
            )
            return redirect(USERS_LIST_URL)
        return super().dispatch(request, *args, **kwargs)


class TeamAdminPermissions(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, UNAUTHORIZED_MESSAGE)
            return redirect('login')

        team = self.get_object()
        if not team.is_admin(request.user):
            messages.error(
                request,
                _("You don't have permissions to modify this."
                  " Only team admin can do this.")
            )
            return redirect(USERS_LIST_URL)

        return super().dispatch(request, *args, **kwargs)


class TeamMembershipAdminPermissions(LoginRequiredMixin):

    def dispatch(self, request, *args, **kwargs):
        from task_manager.teams.models import TeamMembership

        if not request.user.is_authenticated:
            messages.error(request, UNAUTHORIZED_MESSAGE)
            return redirect('login')

        try:
            membership = TeamMembership.objects.get(uuid=kwargs['uuid'])
            team = membership.team

            # check if user is team admin or not
            if not team.is_admin(request.user):
                messages.error(
                    request,
                    _("You don't have permissions to manage team members."
                      " Only team admin can do this.")
                )
                return redirect('teams:team-detail', uuid=team.uuid)

            # check if user is trying to change their own role
            if membership.user == request.user:
                messages.error(
                    request,
                    _("You cannot change your own role in the team.")
                )
                return redirect('teams:team-detail', uuid=team.uuid)

        except TeamMembership.DoesNotExist:
            messages.error(request, _("Team membership not found."))
            return redirect(USERS_LIST_URL)

        return super().dispatch(request, *args, **kwargs)
