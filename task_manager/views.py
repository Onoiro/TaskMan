from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render
from django.views import View
from django.utils.translation import gettext as _
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.http import HttpResponse


# use this path '/trigger-error' when need to check connect to rollbar
def trigger_error(request):
    division_by_zero = 1 / 0
    # a = None
    # a.Hello()
    return HttpResponse("This should not be reached")


class IndexView(View):

    def get(self, request, *args, **kwargs):
        content = {
            'hello_from_hexlet': _("Hello from Hexlet!"),
            'coding_courses': _('Practical programming courses'),
            'read_more': _("Read more"),
        }
        return render(request, 'index.html', context=content)


class UserLoginView(LoginView):
    template_name = 'login.html'

    def form_valid(self, form: AuthenticationForm):
        messages.success(self.request, _("You successfully logged in"))
        return super().form_valid(form)


class UserLogoutView(LogoutView):

    def dispatch(self, request, *args, **kwargs):
        messages.info(request, _("You are logged out"))
        return super().dispatch(request, *args, **kwargs)
