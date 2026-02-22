from django.urls import path
from task_manager.teams.views import (
    TeamCreateView,
    TeamDetailView,
    TeamUpdateView,
    TeamDeleteView,
    TeamExitView,
    TeamMemberRoleUpdateView,
)
from .views import SwitchTeamView

app_name = 'teams'

urlpatterns = [
    path('create/', TeamCreateView.as_view(), name='team-create'),
    path('<uuid:uuid>/detail/', TeamDetailView.as_view(), name='team-detail'),
    path('<uuid:uuid>/update/', TeamUpdateView.as_view(), name='team-update'),
    path('<uuid:uuid>/delete/', TeamDeleteView.as_view(), name='team-delete'),
    path('<uuid:uuid>/exit/', TeamExitView.as_view(), name='team-exit'),
    path('switch/', SwitchTeamView.as_view(), name='switch-team'),
    path('membership/<uuid:uuid>/update-role/',
         TeamMemberRoleUpdateView.as_view(),
         name='team-member-role-update'),
]
