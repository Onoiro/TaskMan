from django.contrib.messages.views import SuccessMessageMixin
from task_manager.permissions import CustomPermissions, UserPermissions
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from task_manager.user.forms import UserForm
from task_manager.user.models import User
from task_manager.tasks.models import Task
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth import login, update_session_auth_hash


import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "task_manager.settings")
django.setup()


class UserListView(ListView):
    model = User
    template_name = 'user/user_list.html'

    def get_queryset(self):
        current_user = self.request.user
        if not current_user.is_authenticated:
            return User.objects.none()

        team = getattr(self.request, 'active_team', None)

        if team:
            team_users = User.objects.filter(
                team_memberships__team=team
            ).distinct()
            return team_users
        else:
            return User.objects.filter(id=current_user.id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        team = getattr(self.request, 'active_team', None)

        if team:
            from task_manager.teams.models import TeamMembership
            # get all memberships in current active team
            context['user_memberships'] = (
                TeamMembership.objects.filter(team=team)
            )
            # get membership of current user
            try:
                context['user_membership'] = TeamMembership.objects.get(
                    user=self.request.user,
                    team=team
                )
            except TeamMembership.DoesNotExist:
                context['user_membership'] = None
        else:
            context['user_memberships'] = []
            context['user_membership'] = None

        return context


class UserDetailView(DetailView):
    model = User
    template_name = 'user/user_detail.html'
    context_object_name = 'object'
    slug_field = 'username'
    slug_url_kwarg = 'username'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.object

        # get user's teams
        from task_manager.teams.models import TeamMembership
        user_teams = TeamMembership.objects.filter(user=user)
        context['user_teams'] = user_teams

        # Check if current user can change role of this user
        context['can_change_role'] = False
        context['membership_uuid'] = None
        context['active_team'] = getattr(self.request, 'active_team', None)

        is_authenticated = self.request.user.is_authenticated
        is_different_user = self.request.user != user
        has_active_team = context['active_team']

        if is_authenticated and is_different_user and has_active_team:

            # Check if current user is admin of the active team
            if context['active_team'].is_admin(self.request.user):
                # Get membership of the viewed user in active team
                try:
                    membership = TeamMembership.objects.get(
                        user=user,
                        team=context['active_team']
                    )
                    context['membership_uuid'] = membership.uuid
                    context['can_change_role'] = True
                except TeamMembership.DoesNotExist:
                    pass

        return context


class UserCreateView(SuccessMessageMixin, CreateView):
    form_class = UserForm
    template_name = 'user/user_create_form.html'
    success_url = reverse_lazy('index')
    success_message = _('User created successfully')

    def form_valid(self, form):
        user = form.save(commit=True, request=self.request)
        # auto login after creating user
        login(self.request, user)

        # Set flag to redirect to tasks list on first visit
        self.request.session['redirect_after_login'] = True

        # if join to team
        team = form.cleaned_data.get('team_to_join')
        if team:
            self.request.session['active_team_uuid'] = str(team.uuid)
            messages.success(
                self.request,
                _(
                    "Welcome! You have joined team: {team}"
                ).format(team=team.name)
            )
        else:
            messages.info(
                self.request,
                _("Welcome! You can create a team or work individually")
            )

        return redirect('index')


class UserUpdateView(CustomPermissions,
                     UserPermissions,
                     SuccessMessageMixin,
                     UpdateView):
    model = User
    form_class = UserForm
    template_name = 'user/user_update.html'
    redirect_field_name = "redirect_to"
    success_url = reverse_lazy('user:user-list')
    success_message = _('User updated successfully')
    slug_field = 'username'
    slug_url_kwarg = 'username'

    def form_valid(self, form):
        # Step 1: Save the user object to database and store it
        # We use self.object so the redirect URL works correctly
        self.object = form.save(commit=True, request=self.request)

        # Step 2: Keep the user session active after password change
        # Without this, the user would be logged out after changing password
        if self.request.user == self.object:
            update_session_auth_hash(self.request, self.object)

        # Step 3: Handle team change logic
        # Check if user selected a new team to join
        team = form.cleaned_data.get('team_to_join')
        if team:
            # Save the new team ID in the session
            self.request.session['active_team_uuid'] = str(team.uuid)
            # Show message to user about joining the team
            messages.success(
                self.request,
                _("You have joined team: {team}").format(team=team.name)
            )

        # Step 4: Add success message manually
        # We call super() in a different way,
        # so we need to add this message ourselves
        success_message = self.get_success_message(form.cleaned_data)
        if success_message:
            messages.success(self.request, success_message)

        # Step 5: Redirect user to the success page
        # We return redirect instead of calling the parent method
        return redirect(self.get_success_url())


class UserDeleteView(CustomPermissions,
                     UserPermissions,
                     SuccessMessageMixin,
                     DeleteView):
    model = User
    template_name = 'user/user_delete.html'
    success_url = reverse_lazy('index')
    success_message = _('User deleted successfully')
    slug_field = 'username'
    slug_url_kwarg = 'username'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        # check if user is admin of any team
        from task_manager.teams.models import TeamMembership
        admin_memberships = TeamMembership.objects.filter(
            user=self.object,
            role='admin'
        )

        if admin_memberships.exists():
            team_names = ', '.join([m.team.name for m in admin_memberships])
            messages.error(
                self.request,
                _(
                    f"Cannot delete user because they are admin of team(s): "
                    f"{team_names}. "
                    "Transfer admin rights or delete the team(s) first.")
            )
            return redirect('user:user-list')

        # check for user's tasks (author and exucutor)
        user_tasks_as_author = Task.objects.filter(author=self.object)
        user_tasks_as_executor = Task.objects.filter(executor=self.object)

        if user_tasks_as_author.exists() or user_tasks_as_executor.exists():
            messages.error(
                self.request,
                _("Cannot delete a user because it is in use")
            )
            return redirect('user:user-list')

        return super().get(request, *args, **kwargs)
