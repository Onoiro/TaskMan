from django.shortcuts import render, redirect
from django.views import View
from django.utils.translation import gettext as _
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.urls import reverse
from .user.models import User


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


class LoginView():
    pass
    
    # def login_view(request):
    #     if request.method == 'POST':
    #         form = AuthenticationForm(data=request.POST)
    #         if form.is_valid():
    #             username = form.cleaned_data.get('username')
    #             password = form.cleaned_data.get('password')
    #             user = authenticate(username=username, password=password)
    #             if user is not None:
    #                 login(request, user)
    #                 messages.success(request, 'Вы залогинены')
    #                 return redirect(reverse('index'))
    #         messages.error(request, 'Пожалуйста, введите правильные имя пользователя и пароль. Оба поля могут быть чувствительны к регистру.')
    #     else:
    #         form = AuthenticationForm()
    #     return render(request, 'login.html', {'form': form})

    class LogoutView():
        pass
