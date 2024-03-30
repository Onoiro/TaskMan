from django.urls import path

from .views import (
    TasksListView,
    TaskCreateView,
    TaskUpdateView,
    TaskDeleteView
)


app_name = 'tasks'


urlpatterns = [
    path('',
         TasksListView.as_view(), name='tasks-list'),
    path('create/',
         TaskCreateView.as_view(), name='task-create'),
    path('<int:pk>/edit/',
         TaskUpdateView.as_view(), name='task-update'),
    path('<int:pk>/delete/',
         TaskDeleteView.as_view(), name='task-delete'),
]