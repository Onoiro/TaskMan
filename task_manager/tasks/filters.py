import django_filters
from django import forms
from task_manager.tasks.models import Task, Label


class TaskFilter(django_filters.FilterSet):
    labels = django_filters.ModelChoiceFilter(
        queryset=Label.objects.all(), widget=forms.Select
        )

    class Meta:
        model = Task
        fields = ['status', 'executor', 'labels']
