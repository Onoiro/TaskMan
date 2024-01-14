from django.shortcuts import redirect, render
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, login
from django.contrib import messages
from .models import User
from .forms import UserForm
from django.utils.translation import gettext as _
from django.urls import reverse_lazy


class UserListView(ListView):
    model = User
    form_class = UserForm()
    context_object_name = 'users_list'
    template_name = 'user_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Добавление дополнительной информации в контекст
        num_visits = self.request.session.get('num_visits', 0)
        self.request.session['num_visits'] = num_visits+1
        context['is_authenticated'] = self.request.user.is_authenticated
        context['num_visits'] = self.request.session.get('num_visits', 0)
        return context


class UserCreateView(CreateView):
    model = User
    form_class = UserForm
    template_name = 'user/user_create_form.html'
    success_url = reverse_lazy('login')

    def save_user(self, request, *args, **kwargs):
        if request.method == "POST":
            form = UserForm(request.POST)
            if form.is_valid():
                password = form.cleaned_data.get('password')
                password_confirm = form.cleaned_data.get('password_confirm')
                if password == password_confirm:
                    user = form.save()
                    user.save()
                    messages.success(request, 'Пользователь успешно зарегистрирован')
                    return redirect(self.success_url)
                else:
                    messages.error(request, 'The entered passwords do not match.')
                    form = UserForm()
            form = UserForm()
    


class UserUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = User
    form_class = UserForm
    template_name = 'user/user_update.html'
    success_url = reverse_lazy('user-list')

    def test_func(self):
        user = self.get_object()
        return self.request.user == user


class UserDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = User
    template_name = 'user/user_delete.html'
    success_url = 'user-list'

    def test_func(self):
        user = self.get_object()
        return self.request.user == user
