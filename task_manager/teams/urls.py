from django.urls import path
from task_manager.teams.views import (
    TeamCreateView,
    TeamDetailView,
    TeamUpdateView,
    TeamDeleteView,
)

app_name = 'teams'

urlpatterns = [
    path('create/',
         TeamCreateView.as_view(), name='team-create'),
    path('<int:pk>/detail/',
         TeamDetailView.as_view(), name='team-detail'),
    path('<int:pk>/update/',
         TeamUpdateView.as_view(), name='team-update'),
    path('<int:pk>/delete/',
         TeamDeleteView.as_view(), name='team-delete'),
]
