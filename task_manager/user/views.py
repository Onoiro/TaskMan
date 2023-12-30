from django.shortcuts import redirect
from django.views.generic import ListView, CreateView
from .models import User
from .forms import UserForm
from django.utils.translation import gettext as _
from django.urls import reverse_lazy


class UserList(ListView):
    model = User
    context_object_name = 'users_list'
    template_name = 'user_list.html'


class UserCreate(CreateView):
    model = User
    form_class = UserForm
    # fields = ['first_name', 'last_name', 'username', 'password']
    template_name = 'user/user_create_form.html'
    success_url = reverse_lazy('user-list')

    def post_new(self, request, *args, **kwargs):
        if request.metod == "POST":
            form = UserForm(request.POST)
            if form.is_valid():
                user = form.save()
                user.save()
                # print(user.username, user.password, user.created_at)
                return redirect(self.success_url)
        else:
            print('Data is not valid')
            form = UserForm()