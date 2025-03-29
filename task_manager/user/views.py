from django.contrib.messages.views import SuccessMessageMixin
from task_manager.permissions import CustomPermissions, UserPermissions
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from task_manager.user.forms import UserForm
# from django.contrib.auth.models import User
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
        # return user himself if he does not have a command
        if not current_user.team:
            return User.objects.filter(id=current_user.id)
        # return all users of the same team
        return User.objects.filter(team=current_user.team)


class UserCreateView(SuccessMessageMixin,
                     CreateView):
    form_class = UserForm
    template_name = 'user/user_create_form.html'
    success_url = reverse_lazy('teams:team-create')
    success_message = _('User created successfully')

    def form_valid(self, form):
        super().form_valid(form)
        # Auto Login after create user
        login(self.request, self.object)
        # If user is team_admin redirect to create team
        if self.object.is_team_admin:
            return redirect('teams:team-create')
        # Else redirect to Login
        return redirect('login')


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


class UserDeleteView(CustomPermissions,
                     UserPermissions,
                     SuccessMessageMixin,
                     DeleteView):
    model = User
    template_name = 'user/user_delete.html'
    success_url = reverse_lazy('user:user-list')
    success_message = _('User deleted successfully')

    def form_valid(self, form):
        self.object = self.get_object()
        user_tasks_as_author = Task.objects.filter(author=self.object)
        user_tasks_as_executor = Task.objects.filter(executor=self.object)
        if user_tasks_as_author.exists() or user_tasks_as_executor.exists():
            messages.error(self.request,
                           _("Cannot delete a user because it is in use"))
            return redirect('user:user-list')
        return super().form_valid(form)
