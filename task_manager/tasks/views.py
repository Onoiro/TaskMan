from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from task_manager.permissions import CustomPermissions, UNAUTHORIZED_MESSAGE
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.db import models
from django.db.models import Count, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce
from .models import Task, ChecklistItem
from task_manager.notes.models import Note
from task_manager.tasks.forms import TaskForm
from django.shortcuts import redirect, get_object_or_404
from django_filters.views import FilterView
from task_manager.tasks.filters import TaskFilter
from urllib.parse import urlencode
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from task_manager.limit_service import LimitService
import json


# Session keys for storing filter settings (context-aware)
SESSION_FILTER_KEY_PREFIX = 'task_filter_params'
SESSION_FILTER_ENABLED_KEY_PREFIX = 'task_filter_enabled'


def _get_filter_session_keys(request):
    """Get context-aware session keys for filter settings."""
    team = getattr(request, 'active_team', None)
    if team:
        suffix = str(team.uuid)
    else:
        suffix = 'individual'
    return (
        f"{SESSION_FILTER_KEY_PREFIX}_{suffix}",
        f"{SESSION_FILTER_ENABLED_KEY_PREFIX}_{suffix}",
    )


# Service parameters that we do not save
SERVICE_PARAMS = (
    'show_filter',
    'save_as_default',
    'reset_default',
    'view_mode',
    'sort',
)

# Sort options for task list
SORT_OPTIONS = {
    '-updated_at': _('Last updated'),
    'updated_at': _('First updated'),
    '-created_at': _('Newest first'),
    'created_at': _('Oldest first'),
    'name': _('Name A→Z'),
    '-name': _('Name Z→A'),
}
DEFAULT_SORT = '-created_at'


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


class TaskFilterView(CustomPermissions, FilterView):
    model = Task
    template_name = 'tasks/task_filter.html'
    filterset_class = TaskFilter
    paginate_by = 50     

    def get(self, request, *args, **kwargs):
        # Handle reset filter button (removes saved default filter)
        if 'reset_default' in request.GET:
            filter_key, enabled_key = _get_filter_session_keys(request)
            request.session.pop(filter_key, None)
            request.session.pop(enabled_key, None)
            request.session.pop(f'{filter_key}_explicit', None)
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
        """Extract filter parameters from GET (without service params).

        Uses .lists() to properly handle multiple values for the same parameter.
        Returns a dict where each value is a list of non-empty values.
        """
        result = {}
        for k, v_list in request.GET.lists():
            if k in SERVICE_PARAMS:
                continue
            # Filter out empty values and keep only non-empty ones
            filtered_values = [v for v in v_list if v]
            if filtered_values:
                result[k] = filtered_values
        return result

    def _get_sort_param(self):
        """Get validated sort parameter."""
        sort = self.request.GET.get('sort', DEFAULT_SORT)
        if sort not in SORT_OPTIONS:
            sort = DEFAULT_SORT
        return sort

    def _save_filter_to_session(self, request):
        """Save current filter parameters to session."""
        filter_params = self._get_filter_params(request)

        # Don't save empty filter (user cleared all fields)
        if not filter_params:
            return

        filter_key, enabled_key = _get_filter_session_keys(request)

        request.session[filter_key] = filter_params
        request.session[enabled_key] = True
        request.session[f'{filter_key}_explicit'] = True
        messages.success(request, _('Filter saved as default'))

    def _should_apply_saved_filter(self, request):
        """Check if we need to apply the saved filter."""
        # If user is actively filtering - do not interfere
        user_params = self._get_filter_params(request)
        if user_params:
            return False

        # If view_mode parameter exists
        if 'view_mode' in request.GET:
            return False

        # If sort parameter exists
        if 'sort' in request.GET:
            return False

        # Check if saved filter exists (context-aware)
        filter_key, enabled_key = _get_filter_session_keys(request)
        filter_enabled = request.session.get(enabled_key, False)
        saved_params = request.session.get(filter_key, {})

        return filter_enabled and saved_params

    def _redirect_with_saved_filter(self, request):
        """Redirect with saved filter parameters applied."""
        filter_key, _ = _get_filter_session_keys(request)
        saved_params = request.session.get(filter_key, {})
        # saved_params is already in list format from .lists()
        query_string = urlencode(saved_params, doseq=True)
        return redirect(f"{request.path}?{query_string}")

    def get_queryset(self):
        user = self.request.user
        team = getattr(self.request, 'active_team', None)
        sort = self._get_sort_param()

        # Start with base queryset
        qs = Task.objects.all()

        # Filter by team or individual tasks
        if team:
            qs = qs.filter(team=team)
        else:
            qs = qs.filter(author=user, team__isnull=True)

        # Optimize single relations with select_related
        qs = qs.select_related('status', 'author', 'updated_by')

        # Create Subquery annotations for counts to avoid N+1 queries
        # This prevents duplicate rows from ManyToMany JOINs
        notes_count_subq = Note.objects.filter(
            task=OuterRef('pk')
        ).values('task').annotate(c=Count('*')).values('c')

        checklist_total_subq = ChecklistItem.objects.filter(
            task=OuterRef('pk')
        ).values('task').annotate(c=Count('*')).values('c')

        checklist_done_subq = ChecklistItem.objects.filter(
            task=OuterRef('pk'), is_done=True
        ).values('task').annotate(c=Count('*')).values('c')

        # Apply annotations with Coalesce to handle null values
        qs = qs.annotate(
            annotated_notes_count=Coalesce(
                Subquery(notes_count_subq), Value(0)
            ),
            annotated_checklist_total=Coalesce(
                Subquery(checklist_total_subq), Value(0)
            ),
            annotated_checklist_done=Coalesce(
                Subquery(checklist_done_subq), Value(0)
            )
        )

        # Prefetch ManyToMany and reverse relations
        qs = qs.prefetch_related('labels', 'executors', 'notes__author')

        # Apply distinct and ordering
        return qs.distinct().order_by(sort)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Information about saved filter for template rendering (context-aware)
        filter_key, enabled_key = _get_filter_session_keys(self.request)
        saved_params = self.request.session.get(filter_key, {})

        # Check if user explicitly saved this filter (not auto-applied)
        user_explicitly_saved = self.request.session.get(
            f'{filter_key}_explicit', False
        )

        context['saved_filter_params'] = saved_params
        # Checkbox is checked only when user explicitly saved filter
        context['saved_filter_enabled'] = user_explicitly_saved
        context['has_saved_filter'] = bool(saved_params)

        # Count of active filter params (not empty)
        # Use .lists() to properly count multiple values for the same parameter
        # Filter out empty strings from each list of values
        active_filter_count = sum(
            len([v for v in values if v])
            for key, values in self.request.GET.lists()
            if key not in SERVICE_PARAMS
        )
        context['active_filter_count'] = active_filter_count

        # Sort options for template
        current_sort = self._get_sort_param()
        context['current_sort'] = current_sort
        context['current_sort_label'] = SORT_OPTIONS.get(
            current_sort, SORT_OPTIONS[DEFAULT_SORT])
        context['sort_options'] = SORT_OPTIONS
        
        query_params = self.request.GET.copy()
        query_params.pop('page', None)
        context['query_string'] = query_params.urlencode()

        return context


class TaskCreateView(CustomPermissions, SuccessMessageMixin, CreateView):
    form_class = TaskForm
    template_name = 'tasks/task_create_form.html'
    success_message = _('Task created successfully')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, UNAUTHORIZED_MESSAGE)
            return redirect('login')

        service = LimitService(request.user)
        result = service.can_create_task()
        if not result.allowed:
            messages.warning(request, result.message)
            return redirect('tasks:tasks-list')
        return super().dispatch(request, *args, **kwargs)

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
                form.instance._actor = self.request.user
                form.instance.executors.add(self.request.user)
                self.object = form.instance
                return super().form_valid(form)
        else:
            form.instance.save()
            form.instance._actor = self.request.user
            form.instance.executors.add(self.request.user)
            self.object = form.instance
            return super().form_valid(form)

        form.instance._actor = self.request.user
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
        form.instance.updated_by = self.request.user
        form.instance._actor = self.request.user
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add notes related to this task
        context['notes'] = self.object.notes.all().select_related('author')
        return context


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


def _parse_checklist_text_from_request(request):
    """
    Extract checklist text from JSON request body.
    Returns empty string if JSON parsing fails or if text is missing.
    """
    try:
        data = json.loads(request.body)
        return data.get('text', '')
    except (json.JSONDecodeError, TypeError):
        return ''


def _validate_checklist_text(text):
    """
    Validate checklist item text.

    Returns tuple: (cleaned_text, error_message)
    - If text is valid: returns (cleaned_text, None)
    - If text is invalid: returns (None, error_message)
    """
    text = text.strip()

    # Check if text is empty
    if not text:
        return None, _('Text is required')

    # Check if text is too long
    if len(text) > 300:
        return None, _('Text must be 300 characters or less')

    # Text is valid
    return text, None


def _get_next_checklist_position(task):
    """
    Get the next available position number for a checklist item.
    Finds the maximum position and adds 1. Returns 1 if no items exist.
    """
    max_position = task.checklist_items.aggregate(
        models.Max('position')
    )['position__max'] or 0
    return max_position + 1


def _create_checklist_response(item, task):
    """
    Create a JSON response with checklist item data and task progress.
    """
    return JsonResponse({
        'id': item.id,
        'text': item.text,
        'is_done': item.is_done,
        'position': item.position,
        'total': task.checklist_total,
        'done': task.checklist_done,
        'progress': task.checklist_progress,
    })


def _create_checklist_progress_response(task):
    """
    Create a JSON response with task checklist progress data.
    Used after toggling or deleting checklist items.
    """
    return JsonResponse({
        'total': task.checklist_total,
        'done': task.checklist_done,
        'progress': task.checklist_progress,
    })


@login_required
@require_POST
def checklist_add(request, uuid):
    """
    Add a new checklist item to a task.

    Permissions: author, executor, or team admin can add items.
    Limits: user cannot exceed checklist item quota.
    """
    task = get_object_or_404(Task, uuid=uuid)

    # Check if user has permission to edit this task
    error = _check_task_edit_permission(request, task)
    if error:
        return error

    # Check if user can add more checklist items (limit service)
    service = LimitService(request.user)
    result = service.can_add_checklist_item(task)
    if not result.allowed:
        return JsonResponse({'error': str(result.message)}, status=429)

    # Extract and validate text from request
    text = _parse_checklist_text_from_request(request)
    text, error_message = _validate_checklist_text(text)

    if error_message:
        return JsonResponse({'error': error_message}, status=400)

    # Create new checklist item
    position = _get_next_checklist_position(task)
    item = ChecklistItem.objects.create(
        task=task,
        text=text,
        position=position
    )

    return _create_checklist_response(item, task)


@login_required
@require_POST
def checklist_toggle(request, uuid, item_id):
    """
    Toggle the done status of a checklist item (done/not done).

    Permissions: author, executor, or team admin can toggle items.
    """
    task = get_object_or_404(Task, uuid=uuid)

    # Check if user has permission to edit this task
    error = _check_task_edit_permission(request, task)
    if error:
        return error

    item = get_object_or_404(ChecklistItem, id=item_id, task=task)

    # Toggle the done status
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
    """
    Delete a checklist item from a task.

    Permissions: author, executor, or team admin can delete items.
    """
    task = get_object_or_404(Task, uuid=uuid)

    # Check if user has permission to edit this task
    error = _check_task_edit_permission(request, task)
    if error:
        return error

    item = get_object_or_404(ChecklistItem, id=item_id, task=task)

    # Delete the checklist item
    item.delete()

    return JsonResponse({
        'deleted': True,
        'total': task.checklist_total,
        'done': task.checklist_done,
        'progress': task.checklist_progress,
    })
