from django.urls import path
from .views import (
    StatusesListView,
    StatusesCreateView,
    StatusesUpdateView,
    StatusesDeleteView,
)


app_name = 'statuses'


urlpatterns = [
    path('',
         StatusesListView.as_view(),
         name='statuses-list'),
    path('create/',
         StatusesCreateView.as_view(),
         name='statuses-create'),
    path('<int:pk>/update/',
         StatusesUpdateView.as_view(),
         name='statuses-update'),
    path('<int:pk>/delete/',
         StatusesDeleteView.as_view(),
         name='statuses-delete'),
]
