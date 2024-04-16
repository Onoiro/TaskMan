from django.urls import path

from task_manager.tasks.views import (
    TaskFilterView,
    TaskDetailView,
    TaskCreateView,
    TaskUpdateView,
    TaskDeleteView
)
# from django_filters.views import FilterView
from task_manager.tasks.models import Task


app_name = 'tasks'


urlpatterns = [
#     path('',
#          TasksListView.as_view(), name='tasks-list'),
    path('', TaskFilterView.as_view(model=Task), name="tasks-list"),
    path('<int:pk>',
         TaskDetailView.as_view(), name='task-detail'),
    path('create/',
         TaskCreateView.as_view(), name='task-create'),
    path('<int:pk>/edit/',
         TaskUpdateView.as_view(), name='task-update'),
    path('<int:pk>/delete/',
         TaskDeleteView.as_view(), name='task-delete'),
]
