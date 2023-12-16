from django.shortcuts import render
from django.views import View
from django.utils.translation import gettext as _


class IndexView(View):
    def get(self, request, *args, **kwargs):
        users = _("Users")
        exit = _("Exit")
        return render(request, 'user/index.html',
                    context={'users': users,
                            'exit': exit,
                            })

