from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from task_manager.permissions import CustomPermissions
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from .models import Status
from task_manager.statuses.forms import StatusForm
from task_manager.user.models import User
from django.shortcuts import redirect


class StatusesListView(CustomPermissions, ListView):
    model = Status
    template_name = 'statuses/statuses_list.html'

    def get_queryset(self):
        user = self.request.user
        # Используем active_team из request
        team = getattr(self.request, 'active_team', None)
        
        if team:
            # Показываем статусы команды
            return Status.objects.filter(team=team)
        else:
            # Показываем индивидуальные статусы
            return Status.objects.filter(
                creator=user,
                team__isnull=True
            )
    # def get_queryset(self):
    #     user = self.request.user
    #     if user.team is None:
    #         return Status.objects.filter(creator=user)
    #     team_users = User.objects.filter(team=user.team)
    #     return Status.objects.filter(creator__in=team_users)


class StatusesDetailView(CustomPermissions, DetailView):
    model = Status
    template_name = 'statuses/status_detailed.html'


class StatusesCreateView(SuccessMessageMixin, CreateView):
    form_class = StatusForm
    template_name = 'statuses/statuses_create_form.html'
    success_url = reverse_lazy('statuses:statuses-list')
    success_message = _('Status created successfully')

    def form_valid(self, form):
        status = form.save(commit=False)
        status.creator = self.request.user

        # Устанавливаем команду, если работаем в командном режиме
        team = getattr(self.request, 'active_team', None)
        if team:
            status.team = team

        status.save()
        return super().form_valid(form)


class StatusesUpdateView(CustomPermissions, SuccessMessageMixin, UpdateView):
    model = Status
    form_class = StatusForm
    template_name = 'statuses/statuses_update.html'
    success_url = reverse_lazy('statuses:statuses-list')
    success_message = _('Status updated successfully')


class StatusesDeleteView(CustomPermissions, SuccessMessageMixin, DeleteView):
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
            return redirect('statuses:statuses-list')
        return super().form_valid(form)
