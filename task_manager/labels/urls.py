from django.urls import path
from .views import (
    LabelsListView,
    LabelsCreateView,
    LabelsUpdateView,
    LabelsDeleteView
)

app_name = 'labels'


urlpatterns = [
    path('',
         LabelsListView.as_view(),
         name='labels-list'),
    path('create/',
         LabelsCreateView.as_view(),
         name='labels-create'),
    path('<uuid:uuid>/update/',
         LabelsUpdateView.as_view(),
         name='labels-update'),
    path('<uuid:uuid>/delete/',
         LabelsDeleteView.as_view(),
         name='labels-delete'),
]
