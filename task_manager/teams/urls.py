from django.urls import path
from task_manager.teams.views import (
    TeamCreateView,
    TeamDetailView,
    TeamUpdateView,
    TeamDeleteView,
    TeamJoinView,
    TeamExitView,
    TeamMemberRoleUpdateView,
)
from .views import SwitchTeamView

app_name = 'teams'

urlpatterns = [
    path('create/', TeamCreateView.as_view(), name='team-create'),
    path('join/', TeamJoinView.as_view(), name='team-join'),
    path('<int:pk>/join/', TeamJoinView.as_view(), name='team-join'),
    path('<int:pk>/detail/', TeamDetailView.as_view(), name='team-detail'),
    path('<int:pk>/update/', TeamUpdateView.as_view(), name='team-update'),
    path('<int:pk>/delete/', TeamDeleteView.as_view(), name='team-delete'),
    path('<int:team_id>/exit/', TeamExitView.as_view(), name='team-exit'),
    path('switch/', SwitchTeamView.as_view(), name='switch-team'),
    path('membership/<int:pk>/update-role/', TeamMemberRoleUpdateView.as_view(),
         name='team-member-role-update'),
]
