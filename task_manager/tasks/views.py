from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from task_manager.permissions import CustomPermissions
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.db import models
from .models import Task, ChecklistItem
from task_manager.tasks.forms import TaskForm
from django.shortcuts import redirect, get_object_or_404
from django_filters.views import FilterView
from task_manager.tasks.filters import TaskFilter
from urllib.parse import urlencode
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
import json


# Session keys for storing filter settings
SESSION_FILTER_KEY = 'task_filter_params'
SESSION_FILTER_ENABLED_KEY = 'task_filter_enabled'

# Service parameters that we do not save
SERVICE_PARAMS = ('show_filter', 'save_as_default', 'reset_default')


class TaskDeletePermissionMixin():
    def dispatch(self, request, *args, **kwargs):
        task = self.get_object()
        is_author = task.author == request.user
        is_team_admin = (
            task.team
            and task.team.is_admin(request.user)
        )
        if not is_author and not is_team_admin:
            messages.error(
                request,
                _("Task can only be deleted by its author or team admin.")
            )
            return redirect('tasks:tasks-list')
        return super().dispatch(request, *args, **kwargs)


class TaskUpdatePermissionMixin():
    def dispatch(self, request, *args, **kwargs):
        task = self.get_object()
        is_author = task.author == request.user
        is_executor = request.user in task.executors.all()
        is_team_admin = (
            task.team
            and task.team.is_admin(request.user)
        )
        if not is_author and not is_executor and not is_team_admin:
            messages.error(
                request,
                _("Task can only be updated by its author, executors "
                  "or team admin.")
            )
            return redirect('tasks:tasks-list')
        return super().dispatch(request, *args, **kwargs)


class TaskFilterView(FilterView):
    model = Task
    template_name = 'tasks/task_filter.html'
    filterset_class = TaskFilter

    def get(self, request, *args, **kwargs):
        # Handle reset filter button (removes saved default filter)
        if 'reset_default' in request.GET:
            request.session.pop(SESSION_FILTER_KEY, None)
            request.session.pop(SESSION_FILTER_ENABLED_KEY, None)
            # Redirect to clean list with open filter panel
            show_filter = request.GET.get('show_filter', '')
            if show_filter:
                return redirect(f"{request.path}?show_filter=1")
            return redirect(request.path)

        # Handle saving filter (when checkbox is checked and form is submitted)
        if 'save_as_default' in request.GET:
            self._save_filter_to_session(request)

        # If no filter parameters - apply the saved filter
        if self._should_apply_saved_filter(request):
            return self._redirect_with_saved_filter(request)

        return super().get(request, *args, **kwargs)

    def _get_filter_params(self, request):
        """Extract filter parameters from GET (without service parameters)."""
        return {
            k: v for k, v in request.GET.items()
            if k not in SERVICE_PARAMS and v
        }

    def _save_filter_to_session(self, request):
        """Save current filter parameters to session."""
        filter_params = self._get_filter_params(request)
        request.session[SESSION_FILTER_KEY] = filter_params
        request.session[SESSION_FILTER_ENABLED_KEY] = True
        messages.success(request, _('Filter saved as default'))

    def _should_apply_saved_filter(self, request):
        """Check if we need to apply the saved filter."""
        # If user is actively filtering - do not interfere
        user_params = self._get_filter_params(request)
        if user_params:
            return False

        # If show_filter parameter exists
        #  - user opened the filter panel, do not redirect
        if 'show_filter' in request.GET:
            return False

        # Check if saved filter exists
        filter_enabled = request.session.get(SESSION_FILTER_ENABLED_KEY, False)
        saved_params = request.session.get(SESSION_FILTER_KEY, {})

        return filter_enabled and saved_params

    def _redirect_with_saved_filter(self, request):
        """Redirect with saved filter parameters applied."""
        saved_params = request.session.get(SESSION_FILTER_KEY, {})
        query_string = urlencode(saved_params)
        return redirect(f"{request.path}?{query_string}")

    def get_queryset(self):
        user = self.request.user
        team = getattr(self.request, 'active_team', None)

        if team:
            return Task.objects.filter(team=team).order_by('-created_at')
        else:
            return Task.objects.filter(
                author=user,
                team__isnull=True
            ).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Information about saved filter for template rendering
        saved_params = self.request.session.get(SESSION_FILTER_KEY, {})
        filter_enabled = self.request.session.get(
            SESSION_FILTER_ENABLED_KEY, False)

        context['saved_filter_params'] = saved_params
        context['saved_filter_enabled'] = filter_enabled
        context['has_saved_filter'] = bool(saved_params)

        # Count of active filter params (not empty)
        active_filter_count = sum(
            1 for key, value in self.request.GET.items()
            if value and key not in SERVICE_PARAMS
        )
        context['active_filter_count'] = active_filter_count

        return context


class TaskCreateView(SuccessMessageMixin, CreateView):
    form_class = TaskForm
    template_name = 'tasks/task_create_form.html'
    success_message = _('Task created successfully')

    def get_success_url(self):
        if 'add_checklist' in self.request.POST:
            return reverse_lazy(
                'tasks:task-update',
                kwargs={'uuid': self.object.uuid}
            ) + '?focus_checklist=1'
        if 'save_and_add_label' in self.request.POST:
            update_url = reverse_lazy(
                'tasks:task-update',
                kwargs={'uuid': self.object.uuid}
            )
            return f"{reverse_lazy('labels:labels-create')}?next={update_url}"
        return reverse_lazy('tasks:tasks-list')

    def form_valid(self, form):
        form.instance.author = self.request.user
        team = getattr(self.request, 'active_team', None)

        if team:
            form.instance.team = team
            if team.memberships.count() == 1:
                form.instance.save()
                form.instance.executors.add(self.request.user)
                self.object = form.instance
                return super().form_valid(form)
        else:
            form.instance.save()
            form.instance.executors.add(self.request.user)
            self.object = form.instance
            return super().form_valid(form)

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
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'

    def get_success_url(self):
        if 'add_checklist' in self.request.POST:
            return reverse_lazy(
                'tasks:task-update',
                kwargs={'uuid': self.object.uuid}
            ) + '?focus_checklist=1'
        if 'save_and_add_label' in self.request.POST:
            update_url = reverse_lazy(
                'tasks:task-update',
                kwargs={'uuid': self.object.uuid}
            )
            return f"{reverse_lazy('labels:labels-create')}?next={update_url}"
        return reverse_lazy('tasks:tasks-list')

    def form_valid(self, form):
        return super().form_valid(form)

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
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'


def _check_task_edit_permission(request, task):
    """Check if user can edit task (author, executor or team admin)."""
    is_author = task.author == request.user
    is_executor = request.user in task.executors.all()
    is_team_admin = task.team and task.team.is_admin(request.user)

    if not is_author and not is_executor and not is_team_admin:
        return JsonResponse(
            {'error': _("Task can only be updated by its author, "
                        "executors or team admin.")},
            status=403
        )
    return None


@login_required
@require_POST
def checklist_add(request, uuid):
    """Add a new checklist item to a task."""
    task = get_object_or_404(Task, uuid=uuid)
    error = _check_task_edit_permission(request, task)
    if error:
        return error

    try:
        data = json.loads(request.body)
        text = data.get('text', '').strip()
    except (json.JSONDecodeError, TypeError):
        text = ''.strip()

    if not text:
        return JsonResponse({'error': _('Text is required')}, status=400)

    if len(text) > 300:
        return JsonResponse(
            {'error': _('Text must be 300 characters or less')},
            status=400
        )

    # Get next position
    max_position = task.checklist_items.aggregate(
        models.Max('position')
    )['position__max'] or 0

    item = ChecklistItem.objects.create(
        task=task,
        text=text,
        position=max_position + 1
    )

    return JsonResponse({
        'id': item.id,
        'text': item.text,
        'is_done': item.is_done,
        'position': item.position,
        'total': task.checklist_total,
        'done': task.checklist_done,
        'progress': task.checklist_progress,
    })


@login_required
@require_POST
def checklist_toggle(request, uuid, item_id):
    """Toggle is_done status of a checklist item."""
    task = get_object_or_404(Task, uuid=uuid)
    error = _check_task_edit_permission(request, task)
    if error:
        return error

    item = get_object_or_404(ChecklistItem, id=item_id, task=task)

    item.is_done = not item.is_done
    item.save()

    return JsonResponse({
        'id': item.id,
        'is_done': item.is_done,
        'total': task.checklist_total,
        'done': task.checklist_done,
        'progress': task.checklist_progress,
    })


@login_required
@require_POST
def checklist_delete(request, uuid, item_id):
    """Delete a checklist item."""
    task = get_object_or_404(Task, uuid=uuid)
    error = _check_task_edit_permission(request, task)
    if error:
        return error

    item = get_object_or_404(ChecklistItem, id=item_id, task=task)

    item.delete()

    return JsonResponse({
        'deleted': True,
        'total': task.checklist_total,
        'done': task.checklist_done,
        'progress': task.checklist_progress,
    })
