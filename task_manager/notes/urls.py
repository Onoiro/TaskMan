from django.urls import path

from task_manager.notes.views import (
    NoteListView,
    NoteCreateView,
    NoteDetailView,
    NoteUpdateView,
    NoteDeleteView,
    NoteImageDetailView,
    NoteImageDeleteView,
    NoteFileDownloadView,
    NoteFileDeleteView,
)


app_name = 'notes'


urlpatterns = [
    path('',
         NoteListView.as_view(),
         name='note-list'),
    path('create/',
         NoteCreateView.as_view(),
         name='note-create'),
    path('<uuid:uuid>/',
         NoteDetailView.as_view(),
         name='note-detail'),
    path('<uuid:uuid>/update/',
         NoteUpdateView.as_view(),
         name='note-update'),
    path('<uuid:uuid>/delete/',
         NoteDeleteView.as_view(),
         name='note-delete'),
    path('<uuid:uuid>/images/<int:pk>/',
         NoteImageDetailView.as_view(),
         name='note-image-detail'),
    path('images/<int:pk>/delete/',
         NoteImageDeleteView.as_view(),
         name='note-image-delete'),
    path('<uuid:uuid>/files/<int:pk>/download/',
         NoteFileDownloadView.as_view(),
         name='note-file-download'),
    path('files/<int:pk>/delete/',
         NoteFileDeleteView.as_view(),
         name='note-file-delete'),
]
