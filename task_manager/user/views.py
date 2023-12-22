from django.views.generic import ListView
from .models import User
from django.utils.translation import gettext as _


class UserList(ListView):
    model = User
    context_object_name = 'users_list'
    template_name = 'user_list.html'
