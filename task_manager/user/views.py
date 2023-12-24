from django.views.generic import ListView, CreateView
from .models import User
from django.utils.translation import gettext as _


class UserList(ListView):
    model = User
    context_object_name = 'users_list'
    template_name = 'user_list.html'

class UserCreate(CreateView):
    model = User
    template_name = 'user_create_form.html'
    fields = ['first_name', 'last_name', 'username', 'password']
