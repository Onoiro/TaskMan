from django.shortcuts import render
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from .models import Statuses
from task_manager.statuses.forms import StatusForm


class StatusesListView(ListView):
    model = Statuses
    template_name = 'statuses/statuses_list.html'
    context_object_name = 'statuses_list'


class StatusesCreateView(SuccessMessageMixin, CreateView):
    form_class = StatusForm
    template_name = 'statuses/statuses_create_form.html'
    success_url = reverse_lazy('statuses:statuses-list')
    success_message = _('Status created successfully')


class StatusesPermissions(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, _('You are not authorized! Please login.'))
            return super().dispatch(request, *args, **kwargs)
        return super().dispatch(request, *args, **kwargs)


class StatusesUpdateView(StatusesPermissions, SuccessMessageMixin, UpdateView):
    model = Statuses
    form_class = StatusForm
    template_name = 'statuses/statuses_update.html'
    login_url = 'login'
    success_url = reverse_lazy('statuses:statuses-list')
    success_message = _('Status updated successfully')


class StatusesDeleteView(StatusesPermissions, SuccessMessageMixin, DeleteView):
    model = Statuses
    template_name = 'statuses/statuses_delete.html'
    login_url = 'login'
    success_url = reverse_lazy('statuses:statuses-list')
    success_message = _('Status deleted successfully')
