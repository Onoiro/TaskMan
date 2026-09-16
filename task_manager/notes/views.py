import os

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.http import FileResponse, Http404
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from task_manager.notes.models import Note, NoteImage
from task_manager.notes.forms import NoteForm
from task_manager.permissions import CustomPermissions
from task_manager.limit_service import LimitService


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

        return queryset.select_related('author', 'task'
                                       ).prefetch_related('team')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['task_uuid'] = self.request.GET.get('task')
        return context


class NoteCreateView(SuccessMessageMixin, CreateView):
    model = Note
    form_class = NoteForm
    template_name = 'notes/note_form.html'
    success_message = _('Note created successfully')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            service = LimitService(request.user)
            team = getattr(request, 'active_team', None)
            if team:
                result = service.can_create_team_note(team)
            else:
                result = service.can_create_personal_note()
            if not result.allowed:
                messages.warning(request, result.message)
                return redirect('notes:note-list')
        return super().dispatch(request, *args, **kwargs)

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
        response = super().form_valid(form)
        self._attach_images(form.instance)
        return response

    def _attach_images(self, note):
        """Validate and save uploaded images for the note."""
        files = self.request.FILES.getlist('images')
        if not files:
            return

        service = LimitService(self.request.user)
        result = service.can_add_note_images(note, len(files))
        if not result.allowed:
            messages.warning(self.request, result.message)
            return

        order = note.images.count()
        for uploaded_file in files:
            error = validate_image_upload(uploaded_file)
            if error:
                messages.error(self.request, error)
                continue
            NoteImage.objects.create(
                note=note,
                image=uploaded_file,
                order=order
            )
            order += 1

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
        # Allow GET requests (viewing) for team members
        if request.method == 'GET':
            return super().dispatch(request, *args, **kwargs)

        # Only allow POST/PUT/PATCH for author or team admin
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
        # Redirect back to note-detail page
        return reverse_lazy(
            'notes:note-detail',
            kwargs={'uuid': self.object.uuid}
        )

    def get_queryset(self):
        user = self.request.user
        team = getattr(self.request, 'active_team', None)

        if team:
            return Note.objects.filter(team=team).select_related('team')
        else:
            return Note.objects.filter(
                author=user,
                team__isnull=True
            ).select_related('team')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        self._attach_images(form.instance)
        return response

    def _attach_images(self, note):
        """Validate and save uploaded images for the note."""
        files = self.request.FILES.getlist('images')
        if not files:
            return

        service = LimitService(self.request.user)
        result = service.can_add_note_images(note, len(files))
        if not result.allowed:
            messages.warning(self.request, result.message)
            return

        order = note.images.count()
        for uploaded_file in files:
            error = validate_image_upload(uploaded_file)
            if error:
                messages.error(self.request, error)
                continue
            NoteImage.objects.create(
                note=note,
                image=uploaded_file,
                order=order
            )
            order += 1


class NoteDetailView(CustomPermissions, DetailView):
    model = Note
    template_name = 'notes/note_detail.html'
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'

    def get_queryset(self):
        user = self.request.user
        team = getattr(self.request, 'active_team', None)

        if team:
            return Note.objects.filter(team=team).select_related('team')
        else:
            return Note.objects.filter(
                author=user,
                team__isnull=True
            ).select_related('team')


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
            return Note.objects.filter(team=team).select_related('team')
        else:
            return Note.objects.filter(
                author=user,
                team__isnull=True
            ).select_related('team')


def validate_image_upload(uploaded_file):
    """Validate size and extension of an uploaded image.

    Returns an error message or None when the file is valid.
    Content-type check is delegated to Pillow via ImageField.
    """
    from django.core.files.images import get_image_dimensions

    max_bytes = NoteImage.MAX_IMAGE_SIZE_MB * 1024 * 1024
    if uploaded_file.size > max_bytes:
        return _(
            "Image '%(name)s' is too large. "
            "Maximum size is %(max)s MB."
        ) % {'name': uploaded_file.name, 'max': NoteImage.MAX_IMAGE_SIZE_MB}

    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext not in NoteImage.ALLOWED_IMAGE_EXTENSIONS:
        return _(
            "Image '%(name)s' has unsupported format. "
            "Allowed formats: JPEG, PNG, GIF, WebP."
        ) % {'name': uploaded_file.name}

    try:
        width, height = get_image_dimensions(uploaded_file)
    except Exception:
        return _("Image '%(name)s' is corrupted or not a valid image."
                 ) % {'name': uploaded_file.name}
    if width is None or height is None:
        return _("Image '%(name)s' is corrupted or not a valid image."
                 ) % {'name': uploaded_file.name}

    return None


def get_accessible_note(user, active_team, note_uuid):
    """Return a note the user is allowed to see or raise 404."""
    if active_team:
        note = get_object_or_404(Note, uuid=note_uuid, team=active_team)
    else:
        note = get_object_or_404(
            Note, uuid=note_uuid, author=user, team__isnull=True
        )
    return note


class NoteImageDetailView(CustomPermissions, DetailView):
    """Serve note image files privately (no direct MEDIA_URL access)."""

    def get(self, request, *args, **kwargs):
        note = get_accessible_note(
            request.user,
            getattr(request, 'active_team', None),
            kwargs['uuid']
        )
        image = get_object_or_404(NoteImage, pk=kwargs['pk'], note=note)

        if not image.image:
            raise Http404

        image.image.open('rb')
        return FileResponse(
            image.image.file,
            content_type='image/jpeg',
            filename=os.path.basename(image.image.name)
        )


class NoteImageDeleteView(CustomPermissions, DeleteView):
    """Delete a single image from a note."""

    model = NoteImage
    success_message = _('Image deleted successfully')

    def get_queryset(self):
        return NoteImage.objects.select_related('note')

    def dispatch(self, request, *args, **kwargs):
        note = self.get_object().note
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

    def get_success_url(self):
        return reverse_lazy(
            'notes:note-detail',
            kwargs={'uuid': self.object.note.uuid}
        )

    def form_valid(self, form):
        messages.success(self.request, self.success_message)
        return super().form_valid(form)
