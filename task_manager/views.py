from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render
from django.views import View
from django.utils.translation import gettext as _
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from .user.models import User
from django.urls import reverse_lazy


class IndexView(View):
    
    def get(self, request, *args, **kwargs):
        hello_from_hexlet = _("Hello from Hexlet!")
        coding_courses = _('Practical programming courses')
        read_more = _("Read more")
        exit = _("Exit")
        return render(request, 'index.html',
                      context={'hello_from_hexlet': hello_from_hexlet,
                               'coding_courses': coding_courses,
                               'read_more': read_more,
                               'exit': exit,
                               })


class UserLoginView(LoginView):
    template_name = 'login.html'

    def form_valid(self, form: AuthenticationForm):
        messages.success(self.request, "You successfully logged in")
        return super().form_valid(form)
    

class UserLogoutView(LogoutView):
    
    def dispatch(self, request, *args, **kwargs):
        messages.info(request, "You are logged out")
        return super().dispatch(request, *args, **kwargs)
