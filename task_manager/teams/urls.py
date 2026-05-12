from django.urls import path
from task_manager.teams.views import (
    TeamCreateView,
    TeamDetailView,
    TeamUpdateView,
    TeamDeleteView,
    TeamExitView,
    TeamMemberRoleUpdateView,
    TeamJoinView,
    TeamInviteGenerateView,
    TeamJoinInviteView,
)
from .views import SwitchTeamView

app_name = 'teams'

urlpatterns = [
    path('create/', TeamCreateView.as_view(), name='team-create'),
    path('join/', TeamJoinView.as_view(), name='team-join'),
    path('join-invite/<uuid:invite_code>/',
         TeamJoinInviteView.as_view(),
         name='team-join-invite'),
    path('switch/', SwitchTeamView.as_view(), name='switch-team'),
    path('<uuid:uuid>/detail/', TeamDetailView.as_view(), name='team-detail'),
    path(
        '<uuid:uuid>/invite/generate/',
        TeamInviteGenerateView.as_view(),
        name='team-invite-generate'
    ),
    path('<uuid:uuid>/update/', TeamUpdateView.as_view(), name='team-update'),
    path('<uuid:uuid>/delete/', TeamDeleteView.as_view(), name='team-delete'),
    path('<uuid:uuid>/exit/', TeamExitView.as_view(), name='team-exit'),
    path('<uuid:uuid>/remove/<uuid:membership_uuid>/',
         TeamExitView.as_view(),
         name='team-member-remove'),
    path('membership/<uuid:uuid>/update-role/',
         TeamMemberRoleUpdateView.as_view(),
         name='team-member-role-update'),
]
