from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from task_manager.notes.models import Note
from task_manager.notes.forms import NoteForm
from task_manager.permissions import CustomPermissions


class NoteListView(CustomPermissions, ListView):
    model = Note
    template_name = 'notes/note_list.html'
    context_object_name = 'notes'

    def get_queryset(self):
        user = self.request.user
        team = getattr(self.request, 'active_team', None)

        # Filter by task if provided
        task_uuid = self.request.GET.get('task')

        if team:
            queryset = Note.objects.filter(team=team)
        else:
            queryset = Note.objects.filter(
                author=user,
                team__isnull=True
            )

        if task_uuid:
            queryset = queryset.filter(task__uuid=task_uuid)

        return queryset.select_related('author', 'task')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['task_uuid'] = self.request.GET.get('task')
        return context


class NoteDetailView(CustomPermissions, DetailView):
    model = Note
    template_name = 'notes/note_detail.html'
    context_object_name = 'note'
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'

    def get_queryset(self):
        user = self.request.user
        team = getattr(self.request, 'active_team', None)

        if team:
            return Note.objects.filter(team=team).select_related(
                'author', 'task', 'team'
            )
        else:
            return Note.objects.filter(
                author=user,
                team__isnull=True
            ).select_related('author', 'task')


class NoteCreateView(SuccessMessageMixin, CreateView):
    model = Note
    form_class = NoteForm
    template_name = 'notes/note_form.html'
    success_message = _('Note created successfully')

    def get_success_url(self):
        task_uuid = self.request.GET.get('task')
        if task_uuid:
            return reverse_lazy(
                'tasks:task-update',
                kwargs={'uuid': task_uuid}
            )
        return reverse_lazy('notes:note-list')

    def form_valid(self, form):
        form.instance.author = self.request.user
        team = getattr(self.request, 'active_team', None)
        if team:
            form.instance.team = team
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        task_uuid = self.request.GET.get('task')
        if task_uuid:
            from task_manager.tasks.models import Task
            try:
                task = Task.objects.get(uuid=task_uuid)
                initial['task'] = task
            except Task.DoesNotExist:
                pass
        return initial


class NoteUpdatePermissionMixin:
    """Mixin to check update permissions for notes."""

    def dispatch(self, request, *args, **kwargs):
        note = self.get_object()
        is_author = note.author == request.user
        is_team_admin = (
            note.team
            and note.team.is_admin(request.user)
        )
        is_superuser = request.user.is_superuser

        if not is_author and not is_team_admin and not is_superuser:
            messages.error(
                request,
                _("Note can only be edited by its author or team admin.")
            )
            return redirect('notes:note-list')

        return super().dispatch(request, *args, **kwargs)


class NoteDeletePermissionMixin:
    """Mixin to check delete permissions for notes."""

    def dispatch(self, request, *args, **kwargs):
        note = self.get_object()
        is_author = note.author == request.user
        is_team_admin = (
            note.team
            and note.team.is_admin(request.user)
        )
        is_superuser = request.user.is_superuser

        if not is_author and not is_team_admin and not is_superuser:
            messages.error(
                request,
                _("Note can only be deleted by its author or team admin.")
            )
            return redirect('notes:note-list')

        return super().dispatch(request, *args, **kwargs)


class NoteUpdateView(
    NoteUpdatePermissionMixin,
    CustomPermissions,
    SuccessMessageMixin,
    UpdateView
):
    model = Note
    form_class = NoteForm
    template_name = 'notes/note_form.html'
    success_message = _('Note updated successfully')
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'

    def get_success_url(self):
        if self.object.task:
            return reverse_lazy(
                'tasks:task-update',
                kwargs={'uuid': self.object.task.uuid}
            )
        return reverse_lazy('notes:note-list')

    def get_queryset(self):
        user = self.request.user
        team = getattr(self.request, 'active_team', None)

        if team:
            return Note.objects.filter(team=team)
        else:
            return Note.objects.filter(
                author=user,
                team__isnull=True
            )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs


class NoteDeleteView(
    NoteDeletePermissionMixin,
    CustomPermissions,
    SuccessMessageMixin,
    DeleteView
):
    model = Note
    template_name = 'notes/note_confirm_delete.html'
    success_message = _('Note deleted successfully')
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'

    def get_success_url(self):
        task_uuid = self.request.GET.get('task')
        if task_uuid:
            return reverse_lazy(
                'tasks:task-update',
                kwargs={'uuid': task_uuid}
            )
        return reverse_lazy('notes:note-list')

    def get_queryset(self):
        user = self.request.user
        team = getattr(self.request, 'active_team', None)

        if team:
            return Note.objects.filter(team=team)
        else:
            return Note.objects.filter(
                author=user,
                team__isnull=True
            )
