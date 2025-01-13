from django.http import HttpResponse
from django.contrib.messages.views import SuccessMessageMixin
from task_manager.permissions import CustomPermissions, UserPermissions
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from task_manager.teams.forms import TeamForm
# from django.contrib.auth.models import User
from task_manager.user.models import User
from task_manager.teams.models import Team
from django.shortcuts import redirect

def index(request):
    return HttpResponse('teams')

class TeamCreateView(CustomPermissions,
                     SuccessMessageMixin,
                     CreateView):
    form_class = TeamForm
    template_name = 'teams/team_create_form.html'
    success_url = reverse_lazy('login')
    success_message = _('Team created successfully')

    def form_valid(self, form):
        form.instance.team_admin = self.request.user
        return super().form_valid(form)


# class TeamUpdateView(CustomPermissions,
#                      UserPermissions,
#                      SuccessMessageMixin,
#                      UpdateView):
#     model = Team
#     form_class = UserForm
#     template_name = 'user/user_update.html'
#     redirect_field_name = "redirect_to"
#     success_url = reverse_lazy('user:user-list')
#     success_message = _('User updated successfully')


# class UserDeleteView(CustomPermissions,
#                      UserPermissions,
#                      SuccessMessageMixin,
#                      DeleteView):
#     model = User
#     template_name = 'user/user_delete.html'
#     success_url = reverse_lazy('user:user-list')
#     success_message = _('User deleted successfully')

#     def form_valid(self, form):
#         self.object = self.get_object()
#         user_tasks_as_author = Task.objects.filter(author=self.object)
#         user_tasks_as_executor = Task.objects.filter(executor=self.object)
#         if user_tasks_as_author.exists() or user_tasks_as_executor.exists():
#             messages.error(self.request,
#                            _("Cannot delete a user because it is in use"))
#             return redirect('user:user-list')
#         return super().form_valid(form)