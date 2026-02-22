from django.urls import path
from .views import (
    UserListView,
    UserCreateView,
    UserUpdateView,
    UserDeleteView,
    UserDetailView,
)

app_name = 'user'

urlpatterns = [
    path('', UserListView.as_view(), name='user-list'),
    path('create/', UserCreateView.as_view(), name='user-create'),
    path('<str:username>/',
         UserDetailView.as_view(),
         name='user-detail'),
    path('<str:username>/update/',
         UserUpdateView.as_view(),
         name='user-update'),
    path('<str:username>/delete/',
         UserDeleteView.as_view(),
         name='user-delete'),
]
