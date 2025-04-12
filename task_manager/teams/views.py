from django.http import HttpResponse
from django.contrib.messages.views import SuccessMessageMixin
from task_manager.permissions import CustomPermissions, TeamAdminPermissions
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.detail import DetailView

from task_manager.teams.forms import TeamForm
from task_manager.teams.models import Team


def index(request):
    return HttpResponse('teams')


class TeamCreateView(SuccessMessageMixin,
                     CreateView):
    form_class = TeamForm
    template_name = 'teams/team_create_form.html'
    success_url = reverse_lazy('login')
    success_message = _('Team created successfully')

    def form_valid(self, form):
        # do not save to DB at once
        team = form.save(commit=False)
        # set current user as admin
        team.team_admin = self.request.user
        team.save()
        # add current user as team_admin
        self.request.user.team = team
        self.request.user.save()

        return super().form_valid(form)


class TeamDetailView(DetailView):
    model = Team
    template_name = 'user/user_list.html'


class TeamUpdateView(SuccessMessageMixin,
                     CustomPermissions,
                     TeamAdminPermissions,
                     UpdateView):
    model = Team
    form_class = TeamForm
    template_name = 'teams/team_update.html'
    redirect_field_name = "redirect_to"
    success_message = _('Team updated successfully')
    success_url = reverse_lazy('user:user-list')


class TeamDeleteView(CustomPermissions,
                     TeamAdminPermissions,
                     SuccessMessageMixin,
                     DeleteView):
    model = Team
    template_name = 'teams/team_delete.html'
    success_url = reverse_lazy('user:user-list')
    success_message = _('Team deleted successfully')
