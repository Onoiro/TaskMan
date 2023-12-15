from django.shortcuts import render
from django.utils.translation import gettext as _


def index(request):
    users = _("Users")
    exit = _("Exit")
    return render(request, 'user/index.html',
                  context={'users': users,
                           'exit': exit,
                           })

