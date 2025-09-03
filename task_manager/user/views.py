from django.contrib.messages.views import SuccessMessageMixin
from task_manager.permissions import CustomPermissions, UserPermissions
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from task_manager.user.forms import UserForm
from task_manager.user.models import User
from task_manager.tasks.models import Task
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth import login

import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "task_manager.settings")
django.setup()


class UserListView(ListView):
    model = User
    template_name = 'user/user_list.html'

    def get_queryset(self):
        current_user = self.request.user
        if not current_user.is_authenticated:
            return User.objects.none()
        
        team = getattr(self.request, 'active_team', None)
        
        if team:
            from task_manager.teams.models import TeamMembership
            team_users = User.objects.filter(
                team_memberships__team=team
            ).distinct()
            return team_users
        else:
            return User.objects.filter(id=current_user.id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        team = getattr(self.request, 'active_team', None)
        
        if team:
            from task_manager.teams.models import TeamMembership
            # Получаем все членства в активной команде
            context['user_memberships'] = TeamMembership.objects.filter(team=team)
            # Получаем членство текущего пользователя
            try:
                context['user_membership'] = TeamMembership.objects.get(
                    user=self.request.user,
                    team=team
                )
            except TeamMembership.DoesNotExist:
                context['user_membership'] = None
        else:
            context['user_memberships'] = []
            context['user_membership'] = None
            
        return context

    # def get_queryset(self):
    #     current_user = self.request.user
    #     if not current_user.is_authenticated:
    #         return User.objects.none()
    #     # return user himself if he does not have a command
    #     if not current_user.team:
    #         return User.objects.filter(id=current_user.id)
    #     # return all users of the same team
    #     return User.objects.filter(team=current_user.team)


class UserCreateView(SuccessMessageMixin, CreateView):
    form_class = UserForm
    template_name = 'user/user_create_form.html'
    success_url = reverse_lazy('index')
    success_message = _('User created successfully')

    def form_valid(self, form):
        response = super().form_valid(form)
        # Автоматический вход после создания пользователя
        login(self.request, self.object)
        
        # Если присоединились к команде
        team = form.cleaned_data.get('team_to_join')
        if team:
            self.request.session['active_team_id'] = team.id
            messages.success(
                self.request,
                _(f"Welcome! You have joined team: {team.name}")
            )
        else:
            messages.info(
                self.request,
                _("Welcome! You can create a team or work individually")
            )
            
        return redirect('index')

    # def form_valid(self, form):
    #     super().form_valid(form)
    #     # Auto Login after create user
    #     login(self.request, self.object)
    #     # If user is team_admin redirect to create team
    #     if self.object.is_team_admin:
    #         return redirect('teams:team-create')
    #     return redirect('index')


class UserUpdateView(CustomPermissions,
                     UserPermissions,
                     SuccessMessageMixin,
                     UpdateView):
    model = User
    form_class = UserForm
    template_name = 'user/user_update.html'
    redirect_field_name = "redirect_to"
    success_url = reverse_lazy('user:user-list')
    success_message = _('User updated successfully')

    def form_valid(self, form):
        response = super().form_valid(form)
        # Перелогиниваем пользователя после обновления
        login(self.request, self.object)
        
        # Если присоединились к новой команде
        team = form.cleaned_data.get('team_to_join')
        if team:
            self.request.session['active_team_id'] = team.id
            messages.success(
                self.request,
                _(f"You have joined team: {team.name}")
            )
            
        return redirect('user:user-list')


    # def form_valid(self, form):
    #     super().form_valid(form)
    #     login(self.request, self.object)
    #     if self.object.is_team_admin:
    #         return redirect('teams:team-create')
    #     # return redirect('login')
    #     return redirect('user:user-list')


class UserDeleteView(CustomPermissions,
                     UserPermissions,
                     SuccessMessageMixin,
                     DeleteView):
    model = User
    template_name = 'user/user_delete.html'
    success_url = reverse_lazy('index')
    success_message = _('User deleted successfully')

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        # Проверяем, не является ли пользователь админом какой-либо команды
        from task_manager.teams.models import TeamMembership
        admin_memberships = TeamMembership.objects.filter(
            user=self.object,
            role='admin'
        )
        
        if admin_memberships.exists():
            team_names = ', '.join([m.team.name for m in admin_memberships])
            messages.error(
                self.request,
                _(f"Cannot delete user because they are admin of team(s): {team_names}. "
                  "Transfer admin rights or delete the team(s) first.")
            )
            return redirect('user:user-list')
        
        # Проверяем задачи пользователя
        user_tasks_as_author = Task.objects.filter(author=self.object)
        user_tasks_as_executor = Task.objects.filter(executor=self.object)
        
        if user_tasks_as_author.exists() or user_tasks_as_executor.exists():
            messages.error(
                self.request,
                _("Cannot delete a user because it is in use")
            )
            return redirect('user:user-list')
            
        return super().get(request, *args, **kwargs)

    # def get(self, request, *args, **kwargs):
    #     self.object = self.get_object()
    #     if self.object.team_admin_set.exists():
    #         messages.error(self.request,
    #                        _("Cannot delete a user because it is team admin. "
    #                          "Delete the team first."))
    #         return redirect('user:user-list')
    #     user_tasks_as_author = Task.objects.filter(author=self.object)
    #     user_tasks_as_executor = Task.objects.filter(executor=self.object)
    #     if user_tasks_as_author.exists() or user_tasks_as_executor.exists():
    #         messages.error(self.request,
    #                        _("Cannot delete a user because it is in use"))
    #         return redirect('user:user-list')
    #     return super().get(request, *args, **kwargs)
