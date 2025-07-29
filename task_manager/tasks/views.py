from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from task_manager.permissions import CustomPermissions
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from .models import Task
from task_manager.tasks.forms import TaskForm
from django.shortcuts import redirect
from django_filters.views import FilterView
from task_manager.tasks.filters import TaskFilter
from task_manager.user.models import User
from django.db.models import Q


class TaskDeletePermissionMixin():
    def dispatch(self, request, *args, **kwargs):
        task = self.get_object()
        if not task.author == request.user:
            messages.error(request,
                           _("Task can only be deleted by its author."))
            return redirect('tasks:tasks-list')
        return super().dispatch(request, *args, **kwargs)


class TaskFilterView(FilterView):
    model = Task
    template_name = 'tasks/task_filter.html'
    filterset_class = TaskFilter

    def get_queryset(self):
        user = self.request.user
        if user.team is None:
            return Task.objects.filter(author=user).order_by('-created_at')
        # filter users from the same team with current user
        team_users = User.objects.filter(team=user.team)
        return Task.objects.filter(
            Q(author__in=team_users) | Q(executor__in=team_users)
        ).order_by('-created_at')


class TaskDetailView(CustomPermissions, DetailView):
    model = Task
    template_name = 'tasks/task_detail.html'


class TaskCreateView(SuccessMessageMixin, CreateView):
    form_class = TaskForm
    template_name = 'tasks/task_create_form.html'
    success_url = reverse_lazy('tasks:tasks-list')
    success_message = _('Task created successfully')

    def form_valid(self, form):
        form.instance.author = self.request.user
        # if user have no team, he sets as executor
        if self.request.user.team is None:
            form.instance.executor = self.request.user
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs


class TaskUpdateView(CustomPermissions, SuccessMessageMixin, UpdateView):
    model = Task
    form_class = TaskForm
    template_name = 'tasks/task_update.html'
    success_url = reverse_lazy('tasks:tasks-list')
    success_message = _('Task updated successfully')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs


class TaskDeleteView(TaskDeletePermissionMixin,
                     SuccessMessageMixin, DeleteView):
    model = Task
    template_name = 'tasks/task_delete.html'
    success_url = reverse_lazy('tasks:tasks-list')
    success_message = _('Task deleted successfully')
