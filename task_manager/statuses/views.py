from django.shortcuts import render
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from .models import Statuses
from task_manager.statuses.forms import StatusForm

# def index(request):
#     return render(request, 'statuses/statuses.html', context={
#         'status': 'START',
#     })

class StatusesListView(ListView):
    model = Statuses
    template_name = 'statuses/statuses_list.html'
    context_object_name = 'statuses_list'


class StatusesCreateView(SuccessMessageMixin, CreateView):
    form_class = StatusForm
    template_name = 'statuses/statuses_create_form.html'
    success_url = reverse_lazy('statuses:statuses-list')
    success_message = _('Status created successfully')


class StatusesUpdateView(SuccessMessageMixin, UpdateView):
    model = Statuses
    form_class = StatusForm
    template_name = 'statuses/statuses_update.html'
    success_url = reverse_lazy('statuses:statuses-list')
    success_message = _('Status updated successfully')


class StatusesDeleteView(DeleteView):
    pass
