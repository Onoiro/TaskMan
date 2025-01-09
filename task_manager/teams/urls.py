from django.urls import path
from task_manager.teams import views

# from task_manager.teams.views import (
#     TeamListView,
#     TeamDetailView,
#     TeamCreateView,
#     TeamUpdateView,
#     TeamDeleteView
# )

app_name = 'teams'

# urlpatterns = [path('', views.index),]

from task_manager.teams.views import (
    TeamCreateView,
    # TeamUpdateView,
    # TeamDeleteView
)

urlpatterns = [
    path('create/',
         TeamCreateView.as_view(), name='team-create'),
    # path('<int:pk>/update/',
    #      TeamUpdateView.as_view(), name='team-update'),
    # path('<int:pk>/delete/',
    #      TeamDeleteView.as_view(), name='team-delete'),
]

# urlpatterns = [
#     path('', TeamListView.as_view(), name="teams-list"),
#     path('<int:pk>',
#          TeamDetailView.as_view(), name='team-detail'),
#     path('create/',
#          TeamCreateView.as_view(), name='team-create'),
#     path('<int:pk>/update/',
#          TeamUpdateView.as_view(), name='team-update'),
#     path('<int:pk>/delete/',
#          TeamDeleteView.as_view(), name='team-delete'),
# ]
