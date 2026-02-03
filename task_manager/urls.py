"""
URL configuration for task_manager project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from .views import IndexView, UserLoginView, UserLogoutView
from django.views.generic import TemplateView
from django.views.generic import FileResponse
from django.conf import settings
from . import views


def assetlinks(request):
    with open('/home/abo/taskman/.well-known/assetlinks.json', 'r') as f:
        return FileResponse(f)

urlpatterns = [
    path('trigger-error/', views.trigger_error),
    path('', IndexView.as_view(), name='index'),
    path('feedback/',
         views.FeedbackView.as_view(template_name='feedback.html'),
         name='feedback'),
    path('login/',
         UserLoginView.as_view(template_name='login.html'),
         name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('users/', include('task_manager.user.urls')),
    path('statuses/', include('task_manager.statuses.urls')),
    path('tasks/', include('task_manager.tasks.urls')),
    path('labels/', include('task_manager.labels.urls')),
    path('teams/', include('task_manager.teams.urls')),
    path('admin/', admin.site.urls),
    path('i18n/', include("django.conf.urls.i18n")),
    # (given with Content-Type: application/javascript)
    path('sw.js', TemplateView.as_view(
        template_name='sw.js',
        content_type='application/javascript'
    ), name='sw.js'),
    # (given with Content-Type: application/manifest+json)
    path('manifest.json', TemplateView.as_view(
        template_name='manifest.json',
        content_type='application/manifest+json'
    ), name='manifest.json'),
    path('.well-known/assetlinks.json', assetlinks),
]
