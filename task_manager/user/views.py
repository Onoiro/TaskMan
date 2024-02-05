from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from .forms import UserRegisterForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import redirect


class UserListView(ListView):
    model = User
    template_name = 'user/user_list.html'
    context_object_name = 'users_list'
    

class UserCreateView(SuccessMessageMixin, CreateView):
    form_class = UserRegisterForm
    template_name = 'user/user_create_form.html'
    success_url = reverse_lazy('login')
    success_message = _('User created successfully')


class UserPermissions(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, _('You are not authorized! Please login.'))
            return super().dispatch(request, *args, **kwargs)
        if not self.get_object() == self.request.user:
            messages.error(request, _("You don't have permissions to modify another user."))
            return redirect('user:user-list')
        return super().dispatch(request, *args, **kwargs)


class UserUpdateView(UserPermissions, SuccessMessageMixin, UpdateView):
    model = User
    form_class = UserRegisterForm
    template_name = 'user/user_update.html'
    login_url = 'login'
    redirect_field_name = "redirect_to"
    success_url = reverse_lazy('user:user-list')
    success_message = _('User updated successfully')


class UserDeleteView(UserPermissions, SuccessMessageMixin, DeleteView):
    model = User
    template_name = 'user/user_delete.html'
    login_url = 'login'
    redirect_field_name = "redirect_to"
    success_url = reverse_lazy('user:user-list')
    success_message = _('User deleted successfully')
