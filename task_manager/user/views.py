from django.contrib.auth import login, update_session_auth_hash, logout
from django.contrib.messages.views import SuccessMessageMixin
from task_manager.permissions import CustomPermissions, UserPermissions
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from task_manager.user.forms import UserForm
from task_manager.user.models import User
from django.contrib import messages
from django.shortcuts import redirect


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
            # All users (admin and regular) see only active members
            team_users = User.objects.filter(
                team_memberships__team=team,
                team_memberships__status='active'
            ).distinct()
            return team_users
        else:
            return User.objects.filter(id=current_user.id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        team = getattr(self.request, 'active_team', None)

        if team:
            from task_manager.teams.models import TeamMembership
            is_admin = team.is_admin(self.request.user)

            if is_admin:
                # Admin sees all memberships including pending
                context['user_memberships'] = (
                    TeamMembership.objects.filter(team=team)
                )
                # Get pending memberships for display
                context['pending_memberships'] = (
                    TeamMembership.objects.filter(
                        team=team, status='pending'
                    ).select_related('user')
                )
            else:
                # Regular members see only active memberships
                context['user_memberships'] = (
                    TeamMembership.objects.filter(
                        team=team, status='active'
                    )
                )
                context['pending_memberships'] = []

            # get membership of current user
            try:
                context['user_membership'] = TeamMembership.objects.get(
                    user=self.request.user,
                    team=team
                )
            except TeamMembership.DoesNotExist:
                context['user_membership'] = None

            context['is_team_admin'] = is_admin
        else:
            context['user_memberships'] = []
            context['user_membership'] = None
            context['pending_memberships'] = []
            context['is_team_admin'] = False

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
        active_team = getattr(self.request, 'active_team', None)

        from task_manager.teams.models import TeamMembership
        from task_manager.tasks.models import Task

        context['user_teams'] = TeamMembership.objects.filter(user=user)
        context['team_task_info'] = self._get_team_task_info(
            user, active_team, TeamMembership, Task
        )
        context['individual_task_info'] = self._get_individual_task_info(
            user, active_team, Task
        )
        context['is_own_profile'] = self.request.user == user
        context['active_team'] = active_team
        context['can_view_limits'] = self._can_view_limits(
            user, active_team, TeamMembership
        )

        self._set_role_change_context(
            context, user, active_team, TeamMembership
        )
        return context

    def _can_view_limits(self, user, active_team, TeamMembership):
        """Check if current user can view another user's limits."""
        # Own profile - always can view
        if self.request.user == user:
            return True

        # Superuser can view all
        if self.request.user.is_superuser:
            return True

        # In team mode: admin can view team members' limits
        if active_team and active_team.is_admin(self.request.user):
            try:
                TeamMembership.objects.get(
                    user=user, team=active_team, status='active'
                )
                return True
            except TeamMembership.DoesNotExist:
                pass

        return False

    def _get_team_task_info(self, user, active_team, TeamMembership, Task):
        user_teams = TeamMembership.objects.filter(user=user)
        if self.request.user == user:
            memberships = user_teams
        else:
            if active_team:
                memberships = user_teams.filter(team=active_team)
            else:
                memberships = user_teams.none()

        team_task_info = []
        for membership in memberships:
            team = membership.team
            author_count = Task.objects.filter(
                team=team, author=user
            ).count()
            executor_count = Task.objects.filter(
                team=team, executors=user
            ).count()
            team_task_info.append({
                'team': team,
                'role': membership.role,
                'author_count': author_count,
                'executor_count': executor_count,
            })
        return team_task_info

    def _get_individual_task_info(self, user, active_team, Task):
        # Return individual task info only for own profile
        if self.request.user != user:
            return None
        author_count = Task.objects.filter(
            author=user, team__isnull=True
        ).count()
        executor_count = Task.objects.filter(
            executors=user, team__isnull=True
        ).count()
        return {
            'author_count': author_count,
            'executor_count': executor_count,
        }

    def _set_role_change_context(
        self, context, user, active_team, TeamMembership
    ):
        context['can_change_role'] = False
        context['membership_uuid'] = None

        if (
            self.request.user.is_authenticated
            and self.request.user != user
            and active_team
            and active_team.is_admin(self.request.user)
        ):
            try:
                membership = TeamMembership.objects.get(
                    user=user, team=active_team
                )
                context['membership_uuid'] = membership.uuid
                context['can_change_role'] = True
            except TeamMembership.DoesNotExist:
                pass


class UserCreateView(SuccessMessageMixin, CreateView):
    form_class = UserForm
    template_name = 'user/user_create_form.html'
    success_url = reverse_lazy('index')
    success_message = _('User created successfully')

    def get_initial(self):
        """Set initial form data from query parameters."""
        initial = super().get_initial()
        invite_code = self.request.GET.get('invite_code')
        if invite_code:
            initial['invite_code'] = invite_code
        return initial

    def get_form_kwargs(self):
        """Add initial data to form."""
        kwargs = super().get_form_kwargs()
        invite_code = self.request.GET.get('invite_code')
        if invite_code:
            kwargs['initial'] = kwargs.get('initial', {})
            kwargs['initial']['invite_code'] = invite_code
        return kwargs

    def form_valid(self, form):
        # Add invite_code to cleaned_data if present in GET
        invite_code = self.request.GET.get('invite_code')
        if invite_code:
            form.cleaned_data['invite_code'] = invite_code

        user = form.save(commit=True, request=self.request)
        # auto login after creating user
        login(self.request, user)

        # Set flag to redirect to tasks list on first visit
        self.request.session['redirect_after_login'] = True

        # Check if user joined via invite
        invite_code = self.request.GET.get('invite_code')
        if invite_code:
            messages.success(
                self.request,
                _(
                    "Welcome! Your account has been created and you have "
                    "joined the team."
                )
            )
        else:
            # if join to team via form fields
            team = form.cleaned_data.get('team_to_join')
            if team:
                # User is now pending, don't set as active team
                messages.info(
                    self.request,
                    _(
                        "Your request to join team {team} has been sent. "
                        "Waiting for admin approval."
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
            # Show message about pending approval
            messages.info(
                self.request,
                _(
                    "Your request to join team {team} has been sent. "
                    "Waiting for admin approval."
                ).format(team=team.name)
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
    success_message = _('User account has been deleted')
    slug_field = 'username'
    slug_url_kwarg = 'username'

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        success_url = self.get_success_url()

        # Perform soft delete instead of physical delete
        self.object.soft_delete()

        # Log out the user after deletion
        logout(request)

        messages.success(request, self.success_message)
        return redirect(success_url)
