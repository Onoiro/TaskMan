from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect
from django.views import View
from django.utils import timezone
from django.utils.translation import gettext as _
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from . import forms
from .permissions import CustomPermissions
from .telegram import send_feedback_to_telegram

# Simple in-memory throttle: one feedback message per user per minute.
# Good enough for a small app; a persistent store is not needed yet.
FEEDBACK_THROTTLE_SECONDS = 60
_feedback_last_sent = {}


# use this path '/trigger-error' when need to check connect to rollbar
def trigger_error(request):
    1 / 0


class IndexView(View):

    def get(self, request, *args, **kwargs):
        # Authenticated users are redirected to tasks list:
        # working with tasks is the primary use case of the app.
        # The logo links to /?home=1 so users can still reach
        # the landing page explicitly.
        if request.user.is_authenticated and 'home' not in request.GET:
            return redirect('tasks:tasks-list')
        content = {
            'taskman': _("TaskMan"),
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

    def post(self, request, *args, **kwargs):
        form = forms.FeedbackForm(request.POST)
        if not form.is_valid():
            return JsonResponse({'ok': False, 'errors':
                                 form.errors.get_json_data()}, status=400)

        now = timezone.now()
        last_sent = _feedback_last_sent.get(request.user.pk)
        if last_sent and (now - last_sent).total_seconds() \
                < FEEDBACK_THROTTLE_SECONDS:
            return JsonResponse({
                'ok': False,
                'error': _("You are sending messages too often. "
                           "Please wait a minute."),
            }, status=429)

        subject = form.cleaned_data['subject']
        contact = form.cleaned_data['contact']
        message = form.cleaned_data['message']
        text = (f"Subject: {subject}\n"
                f"From: {contact}\n\n"
                f"{message}")

        sent, error = send_feedback_to_telegram(text)
        if not sent:
            return JsonResponse({'ok': False, 'error': error}, status=502)
        _feedback_last_sent[request.user.pk] = now
        return JsonResponse({'ok': True})


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
