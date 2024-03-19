from django.urls import path

from task_manager.statuses import views

app_name = 'statuses'


urlpatterns = [
    path('', views.index),
]
