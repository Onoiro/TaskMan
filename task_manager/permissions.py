from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.shortcuts import redirect


class CustomPermissions(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request,
                           _('You are not authorized! Please login.'))
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)


class UserPermissions(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if self.request.user != self.get_object():
            messages.error(
                request,
                _("You don't have permissions to modify another user.")
            )
            return redirect('user:user-list')
        return super().dispatch(request, *args, **kwargs)


class TeamAdminPermissions(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        team = self.get_object()
        if not team.is_admin(request.user):
            messages.error(
                request,
                _("You don't have permissions to modify this."
                  " Only team admin can do this.")
            )
            return redirect('user:user-list')

        return super().dispatch(request, *args, **kwargs)
