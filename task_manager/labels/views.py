from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from task_manager.permissions import CustomPermissions
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from .models import Label
from task_manager.labels.forms import LabelForm
from django.shortcuts import redirect


class LabelsListView(CustomPermissions, ListView):
    model = Label
    template_name = 'labels/labels_list.html'

    def get_queryset(self):
        user = self.request.user
        # using active_team from request
        team = getattr(self.request, 'active_team', None)

        if team:
            # show team's labels
            return Label.objects.filter(team=team)
        else:
            # show labels for individual mode
            return Label.objects.filter(
                creator=user,
                team__isnull=True
            )


class LabelsCreateView(SuccessMessageMixin, CreateView):
    form_class = LabelForm
    template_name = 'labels/labels_create.html'
    success_url = reverse_lazy('labels:labels-list')
    success_message = _('Label created successfully')

    def form_valid(self, form):
        label = form.save(commit=False)
        label.creator = self.request.user

        # set team if work with team
        team = getattr(self.request, 'active_team', None)
        if team:
            label.team = team

        label.save()
        return super().form_valid(form)


class LabelsUpdateView(CustomPermissions, SuccessMessageMixin, UpdateView):
    model = Label
    form_class = LabelForm
    template_name = 'labels/labels_update.html'
    success_url = reverse_lazy('labels:labels-list')
    success_message = _('Label updated successfully')

    def get_queryset(self):
        """Override to show only labels that user can update"""
        user = self.request.user
        team = getattr(self.request, 'active_team', None)

        if team:
            # in team mode - can only update labels from this team
            return Label.objects.filter(team=team)
        else:
            # in individual mode - can only update personal labels
            return Label.objects.filter(
                creator=user,
                team__isnull=True
            )


class LabelsDeleteView(CustomPermissions, SuccessMessageMixin, DeleteView):
    model = Label
    template_name = 'labels/labels_delete.html'
    success_url = reverse_lazy('labels:labels-list')
    success_message = _('Label deleted successfully')

    def get_queryset(self):
        """Override to show only labels that user can delete"""
        user = self.request.user
        team = getattr(self.request, 'active_team', None)

        if team:
            return Label.objects.filter(team=team)
        else:
            return Label.objects.filter(
                creator=user,
                team__isnull=True
            )

    def form_valid(self, form):
        label = self.get_object()
        if label.task_set.exists():
            messages.add_message(
                self.request,
                messages.ERROR,
                _("Cannot delete label because it is in use"))
            return redirect('labels:labels-list')
        return super().form_valid(form)
