from django.urls import path

from task_manager.notifications import views

app_name = 'notifications'

urlpatterns = [
    path('<int:pk>/read/', views.mark_read, name='mark-read'),
    path('mark-all-read/', views.mark_all_read, name='mark-all-read'),
]
