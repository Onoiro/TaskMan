from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from .models import Status
from task_manager.statuses.forms import StatusForm
from django.shortcuts import redirect


class StatusesPermissions(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, _('You are not authorized! Please login.'))
            return super().dispatch(request, *args, **kwargs)
        return super().dispatch(request, *args, **kwargs)


class StatusesListView(StatusesPermissions, ListView):
    model = Status
    template_name = 'statuses/statuses_list.html'


class StatusesCreateView(SuccessMessageMixin, CreateView):
    form_class = StatusForm
    template_name = 'statuses/statuses_create_form.html'
    success_url = reverse_lazy('statuses:statuses-list')
    success_message = _('Status created successfully')


class StatusesUpdateView(StatusesPermissions, SuccessMessageMixin, UpdateView):
    model = Status
    form_class = StatusForm
    template_name = 'statuses/statuses_update.html'
    success_url = reverse_lazy('statuses:statuses-list')
    success_message = _('Status updated successfully')


class StatusesDeleteView(StatusesPermissions, SuccessMessageMixin, DeleteView):
    model = Status
    template_name = 'statuses/statuses_delete.html'
    success_url = reverse_lazy('statuses:statuses-list')
    success_message = _('Status deleted successfully')

    def form_valid(self, form):
        status = self.get_object()
        if status.task_set.exists():
            messages.add_message(
                self.request,
                messages.ERROR,
                _("Cannot delete status because it is in use"))
            # Невозможно удалить статус, потому что он используется
            return redirect('statuses:statuses-list')
        return super().form_valid(form)
