from django.http import HttpResponseRedirect
from django.contrib.auth.mixins import LoginRequiredMixin
from task_manager.permissions import (
    TeamAdminPermissions,
    TeamMembershipAdminPermissions
)
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import (
    CreateView,
    UpdateView,
    DeleteView,
    DetailView,
)
from django.contrib import messages
from django.shortcuts import redirect, render

from task_manager.teams.forms import TeamForm, TeamMemberRoleForm, TeamJoinForm
from task_manager.teams.models import Team, TeamMembership
from task_manager.tasks.models import Task
from task_manager.statuses.models import Status
from task_manager.limit_service import LimitService


# Constants
TEAM_NOT_FOUND_MESSAGE = _('Team not found')
USER_LIST_URL = 'user:user-list'


class SwitchTeamView(View):
    def post(self, request):
        team_uuid = request.POST.get('team_uuid')
        referer = request.META.get('HTTP_REFERER', '')

        if team_uuid:
            if team_uuid == 'individual':
                self._switch_to_individual(request)
            else:
                self._switch_to_team(request, team_uuid)

        # Determine redirect URL based on referer
        redirect_url = self._get_redirect_url(referer)

        # If redirecting to tasks list, remove any filter params
        redirect_url = self._clean_filter_params_from_url(redirect_url)

        return redirect(redirect_url)

    def _switch_to_individual(self, request):
        """Switch to individual mode."""
        if 'active_team_uuid' in request.session:
            del request.session['active_team_uuid']
        messages.success(request, _('Switched to individual mode'))

    def _switch_to_team(self, request, team_uuid):
        """Switch to specified team."""
        try:
            team = Team.objects.get(
                uuid=team_uuid,
                memberships__user=request.user
            )
            request.session['active_team_uuid'] = str(team.uuid)
            messages.success(
                request,
                _("Switched to team: {team}").format(team=team.name)
            )
        except Team.DoesNotExist:
            messages.error(request, TEAM_NOT_FOUND_MESSAGE)

    def _clean_filter_params_from_url(self, redirect_url):
        """Remove filter params from URL to prevent cross-context save."""
        if 'tasks' not in redirect_url:
            return redirect_url

        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

        parsed = urlparse(redirect_url)
        query_params = parse_qs(parsed.query)

        filter_params_to_remove = [
            'save_as_default', 'status', 'author',
            'executors', 'labels', 'search',
            'my_tasks', 'has_checklist',
            'created_after', 'created_before',
            'status_exclude', 'author_exclude',
            'executors_exclude', 'labels_exclude',
            'my_tasks_exclude'
        ]

        filtered_params = {
            k: v for k, v in query_params.items()
            if k not in filter_params_to_remove
        }

        new_query = urlencode(filtered_params, doseq=True)
        return urlunparse((
            parsed.scheme, parsed.netloc,
            parsed.path, parsed.params,
            new_query, parsed.fragment
        ))

    def _get_redirect_url(self, referer):
        """Determine where to redirect after team switch"""
        if ('/labels/' in referer
                and ('/update/' in referer or '/delete/' in referer)):
            return 'labels:labels-list'
        if ('/statuses/' in referer
                and ('/update/' in referer or '/delete/' in referer)):
            return 'statuses:statuses-list'
        if ('/tasks/' in referer
                and ('/update/' in referer or '/delete/' in referer)):
            return 'tasks:tasks-list'
        if ('/notes/' in referer
                and ('/update/' in referer or '/delete/' in referer)):
            return 'notes:note-list'
        # Redirect to tasks list if no referer provided
        return referer or 'tasks:tasks-list'


class TeamExitView(LoginRequiredMixin, View):
    def get(self, request, uuid, membership_uuid=None):
        """display confirmation page for exiting team or removing member"""
        try:
            team = Team.objects.get(uuid=uuid)

            # Determine which user is being removed
            target_user, is_removing_self = self._get_target_user(
                request, team, membership_uuid)

            if target_user is None:
                return self._redirect_back(request)

            # Check permissions and constraints
            error = self._check_removal_allowed(
                request, team, target_user, is_removing_self)
            if error:
                return error

            return render(request, 'teams/team_exit.html', {
                'team': team,
                'target_user': target_user,
                'is_removing_self': is_removing_self,
            })

        except Team.DoesNotExist:
            messages.error(request, TEAM_NOT_FOUND_MESSAGE)
            return self._redirect_back(request)

    def _check_removal_allowed(
        self, request, team, target_user, is_removing_self
    ):
        """Check if removal is allowed, return error response or None"""
        if is_removing_self:
            return self._check_self_removal_allowed(request, team)
        else:
            return self._check_admin_removal_allowed(
                request, team, target_user
            )

    def _check_self_removal_allowed(self, request, team):
        """Check if user can leave the team themselves"""
        if not self._is_user_team_member(request.user, team):
            messages.error(request, _('You are not a member of this team'))
            return self._redirect_back(request)

        if self._is_user_team_admin(request.user, team):
            messages.error(
                request,
                _('Team administrators cannot leave the team. '
                  'Please transfer admin rights to another member first.')
            )
            return self._redirect_back(request)

        if self._has_user_tasks_in_team(request.user, team):
            messages.error(
                request,
                self._get_task_error_message(request.user, team))
            return self._redirect_back(request)

        return None

    def _check_admin_removal_allowed(self, request, team, target_user):
        """Check if admin can remove another member"""
        if not team.is_admin(request.user):
            messages.error(
                request,
                _('You do not have rights to manage team members. '
                  'This can only be done by the team administrator'))
            return self._redirect_back(request)

        if not self._is_user_team_member(target_user, team):
            messages.error(request, _('User is not a member of this team'))
            return self._redirect_back(request)

        # Admin can remove any member, no task checks needed
        return None

    def post(self, request, uuid, membership_uuid=None):
        """process exit from team or member removal after confirmation"""
        try:
            team = Team.objects.get(uuid=uuid)

            # Determine which user is being removed
            target_user, is_removing_self = self._get_target_user(
                request, team, membership_uuid)

            if target_user is None:
                return self._redirect_back(request)

            # Check permissions and constraints before removal
            error = self._check_removal_allowed(
                request, team, target_user, is_removing_self)
            if error:
                return error

            # Perform removal and send message
            self._process_removal(
                request, team, target_user, is_removing_self)

            return redirect(USER_LIST_URL)

        except Team.DoesNotExist:
            messages.error(request, TEAM_NOT_FOUND_MESSAGE)
            return self._redirect_back(request)

    def _process_removal(self, request, team, target_user, is_removing_self):
        """handle user removal and send appropriate message"""
        # Clear executors from team tasks before removing membership
        self._clear_user_as_executor(target_user, team)

        # Perform removal
        self._remove_user_membership(target_user, team)

        # Clear session if removing self
        if is_removing_self:
            self._clear_active_team_session(request, team)

        # Send success message
        self._send_removal_message(request, team, target_user, is_removing_self)

    def _clear_user_as_executor(self, user, team):
        """Clear user from executors in all team tasks"""
        tasks = Task.objects.filter(team=team, executors=user)
        for task in tasks:
            task.executors.remove(user)

    def _send_removal_message(
        self, request, team, target_user, is_removing_self
    ):
        """send success message after team removal"""
        if is_removing_self:
            messages.success(
                request,
                _("You have successfully left the team {team}").format(
                    team=team.name)
            )
        else:
            messages.success(
                request,
                _("User {username} has been removed from the team {team}"
                  ).format(
                    username=target_user.username,
                    team=team.name)
            )

    def _get_target_user(self, request, team, membership_uuid):
        """Determine target user and whether user is removing themselves"""
        if membership_uuid:
            # Admin is removing another member
            try:
                membership = TeamMembership.objects.get(uuid=membership_uuid)
                return membership.user, False
            except TeamMembership.DoesNotExist:
                messages.error(request, _('Team membership not found'))
                return None, False
        else:
            # User is leaving themselves
            return request.user, True

    def _is_user_team_member(self, user, team):
        """check if user is a member of the team"""
        return TeamMembership.objects.filter(
            user=user,
            team=team
        ).exists()

    def _is_user_team_admin(self, user, team):
        """check if user is an admin of the team"""
        return TeamMembership.objects.filter(
            user=user,
            team=team,
            role='admin'
        ).exists()

    def _has_user_tasks_in_team(self, user, team):
        """check if user has tasks as author or executor in the team"""
        return (
            Task.objects.filter(team=team, author=user).exists()
            or Task.objects.filter(team=team, executors=user).exists()
        )

    def _get_task_error_message(self, user, team):
        """get appropriate error message for task constraints"""
        has_author_tasks = Task.objects.filter(
            team=team, author=user).exists()
        has_executor_tasks = Task.objects.filter(
            team=team, executors=user).exists()

        if has_author_tasks or has_executor_tasks:
            return _('You cannot exit the team because you are'
                     ' author or executor of tasks in this team.')

    def _remove_user_membership(self, user, team):
        """remove user's membership from the team"""
        TeamMembership.objects.filter(user=user, team=team).delete()

    def _clear_active_team_session(self, request, team):
        """clear active team from session if it matches"""
        if request.session.get('active_team_uuid') == str(team.uuid):
            del request.session['active_team_uuid']

    def _redirect_back(self, request):
        """redirect back to previous page or home"""
        return redirect(request.META.get('HTTP_REFERER', '/'))


class TeamCreateView(LoginRequiredMixin, CreateView):
    model = Team
    form_class = TeamForm
    template_name = 'teams/team_create_form.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            service = LimitService(request.user)
            result = service.can_create_team()
            if not result.allowed:
                messages.warning(request, result.message)
                return redirect('tasks:tasks-list')
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('tasks:tasks-list')

    def form_valid(self, form):
        form.instance = form.save()
        self.object = form.instance

        # create TeamMembership for team creator with role 'admin'
        TeamMembership.objects.create(
            user=self.request.user,
            team=self.object,
            role='admin',
            status='active'
        )

        # create default statuses for new team
        Status.create_default_statuses_for_team(self.object, self.request.user)

        # set the new team as active in session
        self.request.session['active_team_uuid'] = str(self.object.uuid)

        messages.success(self.request, _('Team created successfully'))
        return HttpResponseRedirect(self.get_success_url())


class TeamJoinView(LoginRequiredMixin, View):
    """View for joining an existing team."""

    template_name = 'teams/team_join_form.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            # Check team member limit when user tries to join
            if request.method == 'POST':
                form = TeamJoinForm(
                    request.POST, initial={'user': request.user}
                )
                if form.is_valid():
                    team = form.cleaned_data['team']
                    service = LimitService(request.user)
                    result = service.can_add_team_member(team)
                    if not result.allowed:
                        messages.warning(request, result.message)
                        return redirect('teams:team-join')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        form = TeamJoinForm(initial={'user': request.user})
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = TeamJoinForm(request.POST, initial={'user': request.user})
        if form.is_valid():
            team = form.cleaned_data['team']

            # Create membership as pending (like in user form)
            TeamMembership.objects.create(
                user=request.user,
                team=team,
                role='member',
                status='pending'
            )

            messages.info(
                request,
                _(
                    "Your request to join team {team} has been sent. "
                    "Waiting for admin approval."
                ).format(team=team.name)
            )
            return redirect('tasks:tasks-list')

        return render(request, self.template_name, {'form': form})


class TeamDetailView(LoginRequiredMixin, DetailView):
    model = Team
    template_name = 'teams/team_detail.html'
    context_object_name = 'team'
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        team = self.get_object()

        # get all team members with their roles
        memberships = TeamMembership.objects.filter(
            team=team).select_related('user')
        context['memberships'] = memberships
        context['is_admin'] = team.is_admin(self.request.user)

        return context


class TeamUpdateView(TeamAdminPermissions, UpdateView):
    model = Team
    form_class = TeamForm
    template_name = 'teams/team_update.html'
    success_url = reverse_lazy(USER_LIST_URL)
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'

    def form_valid(self, form):
        messages.success(self.request, _('Team updated successfully'))
        return super().form_valid(form)


class TeamDeleteView(TeamAdminPermissions, DeleteView):
    model = Team
    template_name = 'teams/team_delete.html'
    success_url = reverse_lazy(USER_LIST_URL)
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'

    def form_valid(self, form):
        team = self.get_object()

        # check for tasks in team
        if Task.objects.filter(team=team).exists():
            messages.error(
                self.request,
                _("Cannot delete a team because it has tasks.")
            )
            return redirect(USER_LIST_URL)

        # check for team members
        if team.members.count() > 1:
            messages.error(
                self.request,
                _("Cannot delete a team because it has other members.")
            )
            return redirect(USER_LIST_URL)

        messages.success(self.request, _('Team deleted successfully'))
        return super().form_valid(form)


class TeamMemberRoleUpdateView(TeamMembershipAdminPermissions, UpdateView):
    model = TeamMembership
    form_class = TeamMemberRoleForm
    template_name = 'teams/team_member_role_update.html'
    slug_field = 'uuid'
    slug_url_kwarg = 'uuid'

    def get_success_url(self):
        return reverse_lazy(USER_LIST_URL)

    def form_valid(self, form):
        membership = self.get_object()
        old_role = membership.role
        new_role = form.cleaned_data['role']
        old_status = membership.status
        new_status = form.cleaned_data['status']

        response = super().form_valid(form)

        # Handle role changes
        if old_role != new_role:
            if new_role == 'admin':
                messages.success(
                    self.request,
                    _(
                        "User {username} has been promoted to team admin."
                    ).format(username=membership.user.username)
                )
            else:
                messages.success(
                    self.request,
                    _(
                        "User {username} has been demoted to team member."
                    ).format(username=membership.user.username)
                )

        # Handle status changes (approval)
        if old_status != new_status:
            if new_status == 'active':
                messages.success(
                    self.request,
                    _(
                        "User {username} has been approved and is now "
                        "a member of the team."
                    ).format(username=membership.user.username)
                )
            elif new_status == 'pending':
                messages.warning(
                    self.request,
                    _(
                        "User {username} membership has been set to pending."
                    ).format(username=membership.user.username)
                )

        return response
