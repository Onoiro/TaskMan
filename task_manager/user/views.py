from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from task_manager.permissions import CustomPermissions
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from task_manager.user.forms import UserForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import redirect

import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "task_manager.settings")
django.setup()


class UserPermissions(CustomPermissions):
    
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if not request.user.is_authenticated:
            return response
        if not self.get_object() == self.request.user:
            messages.error(
                request,
                _("You don't have permissions to modify another user."))
            return redirect('user:user-list')
        return response


class UserListView(ListView):
    model = User
    template_name = 'user/user_list.html'


class UserCreateView(SuccessMessageMixin, CreateView):
    form_class = UserForm
    template_name = 'user/user_create_form.html'
    success_url = reverse_lazy('login')
    success_message = _('User created successfully')


# class UserPermissions(LoginRequiredMixin):
#     def dispatch(self, request, *args, **kwargs):
#         if not request.user.is_authenticated:
#             messages.error(request, _('You are not authorized! Please login.'))
#             return super().dispatch(request, *args, **kwargs)
#         if not self.get_object() == self.request.user:
#             messages.error(
#                 request,
#                 _("You don't have permissions to modify another user."))
#             return redirect('user:user-list')
#         return super().dispatch(request, *args, **kwargs)


class UserUpdateView(UserPermissions, SuccessMessageMixin, UpdateView):
    model = User
    form_class = UserForm
    template_name = 'user/user_update.html'
    redirect_field_name = "redirect_to"
    success_url = reverse_lazy('user:user-list')
    success_message = _('User updated successfully')


class UserDeleteView(UserPermissions, SuccessMessageMixin, DeleteView):
    model = User
    template_name = 'user/user_delete.html'
    redirect_field_name = "redirect_to"
    success_url = reverse_lazy('user:user-list')
    success_message = _('User deleted successfully')
