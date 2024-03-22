from django.shortcuts import render
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from .models import Statuses

# def index(request):
#     return render(request, 'statuses/statuses.html', context={
#         'status': 'START',
#     })

class StatusesListView(ListView):
    model = Statuses
    template_name = 'statuses/statuses_list.html'
    context_object_name = 'statuses_list'


class StatusesCreateView(CreateView):
    pass


class StatusesUpdateView(UpdateView):
    pass


class StatusesDeleteView(DeleteView):
    pass
