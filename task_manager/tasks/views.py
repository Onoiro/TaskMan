from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from .models import Task
from task_manager.tasks.forms import TaskForm


# class StatusesPermissions(LoginRequiredMixin):
#     def dispatch(self, request, *args, **kwargs):
#         if not request.user.is_authenticated:
#             messages.error(request, _('You are not authorized! Please login.'))
#             return super().dispatch(request, *args, **kwargs)
#         return super().dispatch(request, *args, **kwargs)


class TasksListView(ListView):
    model = Task
    template_name = 'tasks/tasks_list.html'
    context_object_name = 'statuses_list'


class TaskCreateView(SuccessMessageMixin, CreateView):
    form_class = TaskForm
    template_name = 'tasks/task_create_form.html'
    success_url = reverse_lazy('tasks:tasks-list')
    success_message = _('Task created successfully')


class TaskUpdateView(SuccessMessageMixin, UpdateView):
    model = Task
    form_class = TaskForm
    template_name = 'tasks/task_update.html'
    success_url = reverse_lazy('tasks:tasks-list')
    success_message = _('Task updated successfully')


class TaskDeleteView(SuccessMessageMixin, DeleteView):
    model = Task
    template_name = 'tasks/task_delete.html'
    success_url = reverse_lazy('tasks:tasks-list')
    success_message = _('Task deleted successfully')
