from django.http import HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from task_manager.permissions import CustomPermissions, TeamAdminPermissions
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django import forms
from django.views import View
from django.views.generic import FormView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.detail import DetailView
from django.contrib import messages
from django.shortcuts import redirect

from task_manager.teams.forms import TeamForm
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
    def post(self, request, team_id):
        try:
            team = Team.objects.get(id=team_id)

            if not self._is_user_team_member(request.user, team):
                messages.error(request, _('You are not a member of this team'))
                return self._redirect_back(request)

            # Добавляем проверку на администратора команды
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

            self._remove_user_membership(request.user, team)
            self._clear_active_team_session(request, team)

            messages.success(
                request,
                _(f'You have successfully left the team "{team.name}"')
            )

            return self._redirect_back(request)

        except Team.DoesNotExist:
            messages.error(request, _('Team not found'))
            return self._redirect_back(request)

    def _is_user_team_member(self, user, team):
        """Check if user is a member of the team"""
        return TeamMembership.objects.filter(
            user=user,
            team=team
        ).exists()

    def _is_user_team_admin(self, user, team):
        """Check if user is an admin of the team"""
        return TeamMembership.objects.filter(
            user=user,
            team=team,
            role='admin'
        ).exists()

    def _has_user_tasks_in_team(self, user, team):
        """Check if user has tasks as author or executor in the team"""
        return (
            Task.objects.filter(team=team, author=user).exists()
            or Task.objects.filter(team=team, executor=user).exists()
        )

    def _get_task_error_message(self, user, team):
        """Get appropriate error message for task constraints"""
        has_author_tasks = Task.objects.filter(
            team=team, author=user).exists()
        has_executor_tasks = Task.objects.filter(
            team=team, executor=user).exists()

        if has_author_tasks or has_executor_tasks:
            return _('You cannot exit the team because you are'
                     ' author or executor of tasks in this team.')

    def _remove_user_membership(self, user, team):
        """Remove user's membership from the team"""
        TeamMembership.objects.filter(user=user, team=team).delete()

    def _clear_active_team_session(self, request, team):
        """Clear active team from session if it matches"""
        if request.session.get('active_team_id') == team.id:
            del request.session['active_team_id']

    def _redirect_back(self, request):
        """Redirect back to previous page or home"""
        return redirect(request.META.get('HTTP_REFERER', '/'))


class TeamJoinView(LoginRequiredMixin, FormView):
    template_name = 'teams/team_join.html'
    success_url = reverse_lazy('index')

    def get_form_class(self):
        class TeamJoinForm(forms.Form):
            team_name = forms.CharField(
                label=_('Team name'),
                max_length=150,
                widget=forms.TextInput(attrs={
                    'class': 'form-control',
                    'placeholder': _('Enter team name')
                })
            )
            team_password = forms.CharField(
                label=_('Team password'),
                widget=forms.PasswordInput(attrs={
                    'class': 'form-control',
                    'placeholder': _('Enter team password')
                })
            )

        return TeamJoinForm

    def form_valid(self, form):
        team_name = form.cleaned_data['team_name']
        team_password = form.cleaned_data['team_password']

        try:
            team = Team.objects.get(name=team_name)

            # password validation
            if team.password != team_password:
                messages.error(self.request, _('Invalid team password'))
                return self.form_invalid(form)

            # check if user already in team
            if TeamMembership.objects.filter(
                user=self.request.user,
                team=team
            ).exists():
                messages.warning(
                    self.request,
                    _('You are already a member of this team')
                )
                return redirect('index')

            # create membership
            TeamMembership.objects.create(
                user=self.request.user,
                team=team,
                role='member'
            )

            # set this team as active_team
            self.request.session['active_team_id'] = team.id

            messages.success(
                self.request,
                _(f'Successfully joined team "{team.name}"!')
            )

        except Team.DoesNotExist:
            messages.error(self.request, _('Team not found'))
            return self.form_invalid(form)

        return super().form_valid(form)


class TeamCreateView(SuccessMessageMixin,
                     LoginRequiredMixin,
                     CreateView):
    form_class = TeamForm
    template_name = 'teams/team_create_form.html'
    success_url = reverse_lazy('index')
    success_message = _('Team created successfully')

    def form_valid(self, form):
        response = super().form_valid(form)

        # create membership of user as admin
        TeamMembership.objects.create(
            user=self.request.user,
            team=self.object,
            role='admin'
        )

        # set created team as active_team
        self.request.session['active_team_id'] = self.object.id

        messages.success(
            self.request,
            _(f'Team "{self.object.name}" created successfully! '
              f'You are now the admin.')
        )

        return response


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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_team_admin'] = self.object.is_admin(self.request.user)
        return context


class TeamDeleteView(SuccessMessageMixin,
                     CustomPermissions,
                     TeamAdminPermissions,
                     DeleteView):
    model = Team
    template_name = 'teams/team_delete.html'
    success_url = reverse_lazy('user:user-list')
    success_message = _('Team deleted successfully')

    def post(self, request, *args, **kwargs):
        team = self.get_object()

        # check for team members count
        team_members_count = TeamMembership.objects.filter(team=team).count()

        if team_members_count > 1:  # team has more than 1 member
            messages.error(
                request,
                _("Cannot delete a team because it has other members.")
            )
            return redirect('user:user-list')

        # remove team from session if it's active
        if request.session.get('active_team_id') == team.id:
            del request.session['active_team_id']

        return super().post(request, *args, **kwargs)
