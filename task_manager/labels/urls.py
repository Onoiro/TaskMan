from django.urls import path

from .views import (
    LabelsListView,
    LabelsCreateView,
    LabelsUpdateView,
    LabelsDeleteView
)
from . import views


app_name = 'labels'


urlpatterns = [
    path('',
         LabelsListView.as_view(),
         name='labels-list'),
    path('create/',
         LabelsCreateView.as_view(),
         name='labels-create'),
    path('<int:pk>/edit/',
         LabelsUpdateView.as_view(),
         name='labels-update'),
    path('<int:pk>/delete/',
         LabelsDeleteView.as_view(),
         name='labels-delete'),
]
