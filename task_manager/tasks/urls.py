from django.urls import path

from task_manager.tasks.views import (
    TaskFilterView,
    TaskCreateView,
    TaskUpdateView,
    TaskDeleteView,
    checklist_add,
    checklist_toggle,
    checklist_delete,
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
    path(
        '<uuid:uuid>/checklist/add/',
        checklist_add,
        name='checklist-add'
    ),
    path(
        '<uuid:uuid>/checklist/<int:item_id>/toggle/',
        checklist_toggle,
        name='checklist-toggle'
    ),
    path(
        '<uuid:uuid>/checklist/<int:item_id>/delete/',
        checklist_delete,
        name='checklist-delete'
    ),
]
