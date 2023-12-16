from django.shortcuts import render
from django.views import View
from .models import User
from django.utils.translation import gettext as _


class IndexView(View):
    def get(self, request, *args, **kwargs):
        Users = _("Users")
        users = User.objects.all()
        exit = _("Exit")
        return render(request, 'user/index.html',
                    context={'users': Users,
                             'users': users,
                            'exit': exit,
                            })
