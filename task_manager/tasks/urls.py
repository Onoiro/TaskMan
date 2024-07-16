from django.urls import path

from task_manager.tasks.views import (
    TaskFilterView,
    TaskDetailView,
    TaskCreateView,
    TaskUpdateView,
    TaskDeleteView
)


app_name = 'tasks'


urlpatterns = [
    path('', TaskFilterView.as_view(), name="tasks-list"),
    path('<int:pk>',
         TaskDetailView.as_view(), name='task-detail'),
    path('create/',
         TaskCreateView.as_view(), name='task-create'),
    path('<int:pk>/update/',
         TaskUpdateView.as_view(), name='task-update'),
    path('<int:pk>/delete/',
         TaskDeleteView.as_view(), name='task-delete'),
]
