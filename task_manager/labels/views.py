from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from task_manager.permissions import CustomPermissions
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from .models import Label
from task_manager.labels.forms import LabelForm
from task_manager.user.models import User
from django.shortcuts import redirect


class LabelsPermissions(CustomPermissions):
    pass


class LabelsListView(LabelsPermissions, ListView):
    model = Label
    template_name = 'labels/labels_list.html'

    def get_queryset(self):
        user = self.request.user
        if user.team is None:
            return Label.objects.filter(creator=user)
        team_users = User.objects.filter(team=user.team)
        return Label.objects.filter(creator__in=team_users)


class LabelsCreateView(SuccessMessageMixin, CreateView):
    form_class = LabelForm
    template_name = 'labels/labels_create.html'
    success_url = reverse_lazy('labels:labels-list')
    success_message = _('Label created successfully')

    def form_valid(self, form):
        label = form.save(commit=False)
        label.creator = self.request.user
        label.save()
        return super().form_valid(form)


class LabelsUpdateView(LabelsPermissions, SuccessMessageMixin, UpdateView):
    model = Label
    form_class = LabelForm
    template_name = 'labels/labels_update.html'
    success_url = reverse_lazy('labels:labels-list')
    success_message = _('Label updated successfully')


class LabelsDeleteView(LabelsPermissions, SuccessMessageMixin, DeleteView):
    model = Label
    template_name = 'labels/labels_delete.html'
    success_url = reverse_lazy('labels:labels-list')
    success_message = _('Label deleted successfully')

    def form_valid(self, form):
        label = self.get_object()
        if label.task_set.exists():
            messages.add_message(
                self.request,
                messages.ERROR,
                _("Cannot delete label because it is in use"))
            return redirect('labels:labels-list')
        return super().form_valid(form)
