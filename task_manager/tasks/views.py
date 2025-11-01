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


class TaskDeletePermissionMixin():
    def dispatch(self, request, *args, **kwargs):
        task = self.get_object()
        if not task.author == request.user:
            messages.error(request,
                           _("Task can only be deleted by its author."))
            return redirect('tasks:tasks-list')
        return super().dispatch(request, *args, **kwargs)


class TaskUpdatePermissionMixin():
    def dispatch(self, request, *args, **kwargs):
        task = self.get_object()
        if task.author != request.user and task.executor != request.user:
            messages.error(
                request,
                _("Task can only be updated by its author or executor.")
            )
            return redirect('tasks:tasks-list')
        return super().dispatch(request, *args, **kwargs)


class TaskFilterView(FilterView):
    model = Task
    template_name = 'tasks/task_filter.html'
    filterset_class = TaskFilter

    def get_queryset(self):
        user = self.request.user
        team = getattr(self.request, 'active_team', None)

        if team:
            # show team's tasks
            return Task.objects.filter(team=team).order_by('-created_at')
        else:
            # show individual tasks
            return Task.objects.filter(
                author=user,
                team__isnull=True
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
        team = getattr(self.request, 'active_team', None)

        if team:
            form.instance.team = team
            # if team has only one member - set executor to author
            if team.memberships.count() == 1:
                form.instance.executor = self.request.user
        else:
            # individual task
            form.instance.executor = self.request.user

        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs


class TaskUpdateView(TaskUpdatePermissionMixin,
                     CustomPermissions,
                     SuccessMessageMixin,
                     UpdateView):
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
