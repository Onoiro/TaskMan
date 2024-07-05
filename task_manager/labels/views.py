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
from django.http import HttpResponse


# use this path '/labels/trigger-error' when need to check connect to rollbar
def trigger_error(request):
    division_by_zero = 1 / 0
    # a = None
    # a.Hello()
    return HttpResponse("This should not be reached")


class LabelsPermissions(CustomPermissions):
    pass


class LabelsListView(LabelsPermissions, ListView):
    model = Label
    template_name = 'labels/labels_list.html'


class LabelsCreateView(SuccessMessageMixin, CreateView):
    form_class = LabelForm
    template_name = 'labels/labels_create.html'
    success_url = reverse_lazy('labels:labels-list')
    success_message = _('Label created successfully')


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
