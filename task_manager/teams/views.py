from django.http import HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from task_manager.permissions import (
    TeamAdminPermissions,
    TeamMembershipAdminPermissions
)
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import (
    CreateView,
    UpdateView,
    DeleteView,
    DetailView,
    ListView
)
from django.contrib import messages
from django.shortcuts import redirect, render

from task_manager.teams.forms import TeamForm, TeamMemberRoleForm
from task_manager.teams.models import Team, TeamMembership
from task_manager.tasks.models import Task


def index(request):
    return HttpResponse('teams')


class SwitchTeamView(View):
    def post(self, request):
        team_id = request.POST.get('team_id')

        if team_id:
            if team_id == 'individual':
                # switch to individual mode
                if 'active_team_id' in request.session:
                    del request.session['active_team_id']
                messages.success(request, _('Switched to individual mode'))
            else:
                # switch to team
                try:
                    team = Team.objects.get(
                        id=team_id,
                        memberships__user=request.user
                    )
                    request.session['active_team_id'] = team.id
                    messages.success(
                        request,
                        _(f'Switched to team: {team.name}')
                    )
                except Team.DoesNotExist:
                    messages.error(request, _('Team not found'))

        return redirect(request.META.get('HTTP_REFERER', '/'))


class TeamExitView(LoginRequiredMixin, View):
    def get(self, request, team_id):
        """display confirmation page for exiting team"""
        try:
            team = Team.objects.get(id=team_id)

            # проверки выполняются только в get-методе
            if not self._is_user_team_member(request.user, team):
                messages.error(request, _('You are not a member of this team'))
                return self._redirect_back(request)

            if self._is_user_team_admin(request.user, team):
                messages.error(
                    request,
                    _('Team administrators cannot leave the team. '
                      'Please transfer admin rights to another member first.')
                )
                return self._redirect_back(request)

            if self._has_user_tasks_in_team(request.user, team):
                messages.error(
                    request, self._get_task_error_message(request.user, team))
                return self._redirect_back(request)

            # если дошли сюда - все проверки пройдены, показываем подтверждение
            return render(request, 'teams/team_exit.html', {'team': team})

        except Team.DoesNotExist:
            messages.error(request, _('Team not found'))
            return self._redirect_back(request)

    def post(self, request, team_id):
        """process exit from team after confirmation"""
        # если пользователь дошел до post-запроса, значит он уже прошел все проверки в get
        # и видел страницу подтверждения
        try:
            team = Team.objects.get(id=team_id)
            
            # выполняем выход из команды без дополнительных проверок
            self._remove_user_membership(request.user, team)
            self._clear_active_team_session(request, team)

            messages.success(
                request,
                _(f'You have successfully left the team "{team.name}"')
            )

            return redirect('user:user-list')

        except Team.DoesNotExist:
            messages.error(request, _('Team not found'))
            return self._redirect_back(request)

    def _is_user_team_member(self, user, team):
        """check if user is a member of the team"""
        return TeamMembership.objects.filter(
            user=user,
            team=team
        ).exists()

    def _is_user_team_admin(self, user, team):
        """check if user is an admin of the team"""
        return TeamMembership.objects.filter(
            user=user,
            team=team,
            role='admin'
        ).exists()

    def _has_user_tasks_in_team(self, user, team):
        """check if user has tasks as author or executor in the team"""
        return (
            Task.objects.filter(team=team, author=user).exists()
            or Task.objects.filter(team=team, executor=user).exists()
        )

    def _get_task_error_message(self, user, team):
        """get appropriate error message for task constraints"""
        has_author_tasks = Task.objects.filter(
            team=team, author=user).exists()
        has_executor_tasks = Task.objects.filter(
            team=team, executor=user).exists()

        if has_author_tasks or has_executor_tasks:
            return _('You cannot exit the team because you are'
                     ' author or executor of tasks in this team.')

    def _remove_user_membership(self, user, team):
        """remove user's membership from the team"""
        TeamMembership.objects.filter(user=user, team=team).delete()

    def _clear_active_team_session(self, request, team):
        """clear active team from session if it matches"""
        if request.session.get('active_team_id') == team.id:
            del request.session['active_team_id']

    def _redirect_back(self, request):
        """redirect back to previous page or home"""
        return redirect(request.META.get('HTTP_REFERER', '/'))


class TeamJoinView(LoginRequiredMixin, CreateView):
    model = TeamMembership
    fields = []
    template_name = 'teams/team_join.html'

    def get_success_url(self):
        return reverse_lazy(
            'teams:team-detail',
            kwargs={'pk': self.kwargs['pk']}
        )

    def form_valid(self, form):
        team = Team.objects.get(pk=self.kwargs['pk'])

        # check if user is already a member of the team
        if TeamMembership.objects.filter(
            user=self.request.user, team=team
        ).exists():
            messages.error(self.request, _(
                'You are already a member of this team!'
            ))
            return redirect('teams:team-detail', pk=team.pk)

        form.instance.user = self.request.user
        form.instance.team = team
        form.instance.role = 'member'

        response = super().form_valid(form)
        messages.success(self.request, _(
            'You have successfully joined the team!'
        ))
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['team'] = Team.objects.get(pk=self.kwargs['pk'])
        return context


class TeamCreateView(LoginRequiredMixin, CreateView):
    model = Team
    form_class = TeamForm
    template_name = 'teams/team_create_form.html'
    success_url = reverse_lazy('index')

    def form_valid(self, form):
        response = super().form_valid(form)

        # create TeamMembership for team creator with role 'admin'
        TeamMembership.objects.create(
            user=self.request.user,
            team=self.object,
            role='admin'
        )

        messages.success(self.request, _('Team created successfully'))
        return response


class TeamDetailView(LoginRequiredMixin, DetailView):
    model = Team
    template_name = 'teams/team_detail.html'
    context_object_name = 'team'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        team = self.get_object()

        # get all team members with their roles
        memberships = TeamMembership.objects.filter(
            team=team).select_related('user')
        context['memberships'] = memberships
        context['is_admin'] = team.is_admin(self.request.user)

        return context


class TeamUpdateView(TeamAdminPermissions, UpdateView):
    model = Team
    form_class = TeamForm
    template_name = 'teams/team_update.html'
    success_url = reverse_lazy('user:user-list')

    def form_valid(self, form):
        messages.success(self.request, _('Team updated successfully'))
        return super().form_valid(form)


class TeamDeleteView(TeamAdminPermissions, DeleteView):
    model = Team
    template_name = 'teams/team_delete.html'
    success_url = reverse_lazy('user:user-list')

    def form_valid(self, form):
        team = self.get_object()

        # check for tasks in team
        if Task.objects.filter(team=team).exists():
            messages.error(
                self.request,
                _("Cannot delete a team because it has tasks.")
            )
            return redirect('user:user-list')

        # check for team members
        if team.members.count() > 1:
            messages.error(
                self.request,
                _("Cannot delete a team because it has other members.")
            )
            return redirect('user:user-list')

        messages.success(self.request, _('Team deleted successfully'))
        return super().form_valid(form)


class TeamMemberRoleUpdateView(TeamMembershipAdminPermissions, UpdateView):
    model = TeamMembership
    form_class = TeamMemberRoleForm
    template_name = 'teams/team_member_role_update.html'

    def get_success_url(self):
        return reverse_lazy('user:user-list')

    def form_valid(self, form):
        membership = self.get_object()
        old_role = membership.role
        new_role = form.cleaned_data['role']

        response = super().form_valid(form)

        if old_role != new_role:
            if new_role == 'admin':
                messages.success(
                    self.request,
                    _(f'User {membership.user.username} '
                      'has been promoted to team admin.')
                )
            else:
                messages.success(
                    self.request,
                    _(f'User {membership.user.username} '
                      'has been demoted to team member.')
                )

        return response


class TeamListView(LoginRequiredMixin, ListView):
    model = Team
    template_name = 'teams/team_list.html'
    context_object_name = 'teams'

    def get_queryset(self):
        return Team.objects.all()
