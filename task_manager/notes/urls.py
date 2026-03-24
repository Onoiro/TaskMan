from django.urls import path

from task_manager.notes.views import (
    NoteListView,
    NoteCreateView,
    NoteUpdateView,
    NoteDeleteView,
)


app_name = 'notes'


urlpatterns = [
    path('',
         NoteListView.as_view(),
         name='note-list'),
    path('create/',
         NoteCreateView.as_view(),
         name='note-create'),
    path('<uuid:uuid>/update/',
         NoteUpdateView.as_view(),
         name='note-update'),
    path('<uuid:uuid>/delete/',
         NoteDeleteView.as_view(),
         name='note-delete'),
]
