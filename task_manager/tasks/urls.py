from django.urls import path

from task_manager.tasks.views import (
    TaskFilterView,
    TaskCreateView,
    TaskUpdateView,
    TaskDeleteView
)


app_name = 'tasks'


urlpatterns = [
    path('', TaskFilterView.as_view(), name="tasks-list"),
    path('create/',
         TaskCreateView.as_view(), name='task-create'),
    path('<uuid:uuid>/update/',
         TaskUpdateView.as_view(), name='task-update'),
    path('<uuid:uuid>/delete/',
         TaskDeleteView.as_view(), name='task-delete'),
]
