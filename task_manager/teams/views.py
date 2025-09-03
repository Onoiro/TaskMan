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
from django.db import transaction
from django.shortcuts import redirect, render

from task_manager.teams.forms import TeamForm
from task_manager.teams.models import Team, TeamMembership


def index(request):
    return HttpResponse('teams')


class SwitchTeamView(View):
    def post(self, request):
        team_id = request.POST.get('team_id')

        if team_id:
            if team_id == 'individual':
                # Переключение в индивидуальный режим
                if 'active_team_id' in request.session:
                    del request.session['active_team_id']
                messages.success(request, _('Switched to individual mode'))
            else:
                # Переключение на команду
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

class TeamJoinView(LoginRequiredMixin, FormView):
    """Присоединение к существующей команде"""
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
            
            # Проверяем пароль
            if team.password != team_password:
                messages.error(self.request, _('Invalid team password'))
                return self.form_invalid(form)
            
            # Проверяем, не состоит ли уже в команде
            if TeamMembership.objects.filter(
                user=self.request.user,
                team=team
            ).exists():
                messages.warning(
                    self.request,
                    _('You are already a member of this team')
                )
                return redirect('index')
            
            # Создаем членство
            TeamMembership.objects.create(
                user=self.request.user,
                team=team,
                role='member'
            )
            
            # Устанавливаем команду как активную
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
        # Сохраняем команду
        response = super().form_valid(form)
        
        # Создаем членство с ролью админа для текущего пользователя
        TeamMembership.objects.create(
            user=self.request.user,
            team=self.object,
            role='admin'
        )
        
        # Устанавливаем созданную команду как активную
        self.request.session['active_team_id'] = self.object.id
        
        messages.success(
            self.request,
            _(f'Team "{self.object.name}" created successfully! You are now the admin.')
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
        
        # Проверяем количество участников команды
        team_members_count = TeamMembership.objects.filter(team=team).count()
        
        if team_members_count > 1:  # Больше одного участника (включая админа)
            messages.error(
                request,
                _("Cannot delete a team because it has other members.")
            )
            return redirect('user:user-list')

        # Удаляем команду из сессии, если она была активной
        if request.session.get('active_team_id') == team.id:
            del request.session['active_team_id']

        return super().post(request, *args, **kwargs)
