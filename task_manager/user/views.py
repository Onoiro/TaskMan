from django.shortcuts import render
from django.utils.translation import gettext as _


def index(request):
    users = _("Users")
    return render(request, 'index.html',
                  context={'users': users,
                           })

