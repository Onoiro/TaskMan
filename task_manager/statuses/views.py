from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from .models import Status
from task_manager.statuses.forms import StatusForm


class StatusesPermissions(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, _('You are not authorized! Please login.'))
            return super().dispatch(request, *args, **kwargs)
        return super().dispatch(request, *args, **kwargs)


class StatusesListView(StatusesPermissions, ListView):
    model = Status
    template_name = 'statuses/statuses_list.html'
    login_url = 'login'


class StatusesCreateView(SuccessMessageMixin, CreateView):
    form_class = StatusForm
    template_name = 'statuses/statuses_create_form.html'
    success_url = reverse_lazy('statuses:statuses-list')
    success_message = _('Status created successfully')


class StatusesUpdateView(StatusesPermissions, SuccessMessageMixin, UpdateView):
    model = Status
    form_class = StatusForm
    template_name = 'statuses/statuses_update.html'
    login_url = 'login'
    success_url = reverse_lazy('statuses:statuses-list')
    success_message = _('Status updated successfully')


class StatusesDeleteView(StatusesPermissions, SuccessMessageMixin, DeleteView):
    model = Status
    template_name = 'statuses/statuses_delete.html'
    login_url = 'login'
    success_url = reverse_lazy('statuses:statuses-list')
    success_message = _('Status deleted successfully')
