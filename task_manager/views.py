from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect
from django.views import View
from django.utils.translation import gettext as _
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import HttpResponse
from . import forms
from .permissions import CustomPermissions


# use this path '/trigger-error' when need to check connect to rollbar
def trigger_error(request):
    1 / 0
    return HttpResponse("This should not be reached")


class IndexView(View):

    def get(self, request, *args, **kwargs):
        # Redirect authenticated users to tasks list only on first login
        # The flag is set in UserLoginView after successful login
        if request.user.is_authenticated and \
           request.session.get('redirect_after_login', False):
            # Clear the flag so next click on logo shows index page
            request.session['redirect_after_login'] = False
            return redirect('tasks:tasks-list')
        content = {
            'taskman': _("TaskMan"),
            'manage': _("Personal. Family. Work."),
            'description': _("One planner for everything:"
                             " from notes and personal goals"
                             " to family tasks and team projects."),
            'read_more': _("Read more"),
        }
        return render(request, 'index.html', context=content)


class UserLoginView(LoginView):
    template_name = 'login.html'

    def form_valid(self, form: AuthenticationForm):
        messages.success(self.request, _("You successfully logged in"))
        # Set flag to redirect to tasks list on first visit after login
        # This allows user to access index page by clicking logo later
        self.request.session['redirect_after_login'] = True
        return super().form_valid(form)


class UserLogoutView(LogoutView):

    def dispatch(self, request, *args, **kwargs):
        messages.info(request, _("You are logged out"))
        return super().dispatch(request, *args, **kwargs)


class FeedbackView(CustomPermissions, View):
    template_name = 'feedback.html'

    def get(self, request, *args, **kwargs):
        form = forms.FeedbackForm()
        context = {
            'form': form,
            'title': _("Feedback"),
        }
        return render(request, self.template_name, context)


class LimitsInfoView(LoginRequiredMixin, View):
    template_name = 'limits/limits_info.html'

    def get(self, request):
        from task_manager.limit_service import LimitService
        service = LimitService(request.user)
        usage = service.get_usage_summary()

        # Calculate percentages for each resource
        for key in usage:
            current = usage[key]['current']
            maximum = usage[key]['max']
            if maximum > 0:
                usage[key]['percent'] = min(100, int(current / maximum * 100))
            else:
                usage[key]['percent'] = 0

        context = {
            'usage': usage,
            'limits': service.limits,
        }
        return render(request, self.template_name, context)
