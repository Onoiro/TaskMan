"""
Limit checking service for TaskMan.

Provides methods to check if user can create various resources
based on their subscription plan limits.
"""
from dataclasses import dataclass

from django.utils.translation import gettext_lazy as _

from task_manager.limits import get_user_limits


# Unified limit exceeded message template
LIMIT_EXCEEDED_MESSAGE = _(
    "You're a power user! The %(resource)s limit (%(max)s) has been reached. "
    "Try removing ones you no longer need. "
    "TaskMan Pro without limits is on its way — we're working on it!"
)


@dataclass
class LimitCheckResult:
    """Result of a limit check."""
    allowed: bool
    current: int
    maximum: int
    message: str = ""


class LimitService:
    """Service for checking user resource limits."""

    # Resource names for messages
    RESOURCE_NAMES = {
        'teams': _('teams'),
        'team_members': _('team members'),
        'tasks': _('tasks'),
        'personal_statuses': _('personal statuses'),
        'team_statuses': _('team statuses'),
        'personal_labels': _('personal labels'),
        'team_labels': _('team labels'),
        'personal_notes': _('personal notes'),
        'team_notes': _('team notes'),
        'checklist_items': _('checklist items'),
    }

    def __init__(self, user):
        self.user = user
        self.limits = get_user_limits(user)

    def _get_limit_message(self, resource_key: str, max_value: int) -> str:
        """Generate unified limit exceeded message."""
        resource_name = self.RESOURCE_NAMES.get(resource_key, resource_key)
        return LIMIT_EXCEEDED_MESSAGE % {
            'resource': resource_name,
            'max': max_value
        }

    def can_create_team(self) -> LimitCheckResult:
        from task_manager.teams.models import TeamMembership

        current = TeamMembership.objects.filter(
            user=self.user,
            role='admin'
        ).count()
        max_teams = self.limits.max_teams

        allowed = current < max_teams
        message = ""
        if not allowed:
            message = self._get_limit_message('teams', max_teams)

        return LimitCheckResult(
            allowed=allowed,
            current=current,
            maximum=max_teams,
            message=message
        )

    def can_add_team_member(self, team) -> LimitCheckResult:
        current = team.memberships.filter(status='active').count()
        max_members = self.limits.max_team_members

        allowed = current < max_members
        message = ""
        if not allowed:
            message = self._get_limit_message('team_members', max_members)

        return LimitCheckResult(
            allowed=allowed,
            current=current,
            maximum=max_members,
            message=message
        )

    def can_create_task(self) -> LimitCheckResult:
        from task_manager.tasks.models import Task

        # Count only tasks where user is the author
        # (both personal and team tasks)
        # Tasks are attributed to the author only to avoid double-counting
        # when multiple users are members of the same team
        current = Task.objects.filter(author=self.user).count()
        max_tasks = self.limits.max_tasks_total

        allowed = current < max_tasks
        message = ""
        if not allowed:
            message = self._get_limit_message('tasks', max_tasks)

        return LimitCheckResult(
            allowed=allowed,
            current=current,
            maximum=max_tasks,
            message=message
        )

    def can_create_personal_status(self) -> LimitCheckResult:
        from task_manager.statuses.models import Status

        current = Status.objects.filter(
            creator=self.user,
            team__isnull=True
        ).count()
        max_statuses = self.limits.max_personal_statuses

        allowed = current < max_statuses
        message = ""
        if not allowed:
            message = self._get_limit_message('personal_statuses', max_statuses)

        return LimitCheckResult(
            allowed=allowed,
            current=current,
            maximum=max_statuses,
            message=message
        )

    def can_create_team_status(self, team) -> LimitCheckResult:
        from task_manager.statuses.models import Status

        current = Status.objects.filter(team=team).count()
        max_statuses = self.limits.max_team_statuses

        allowed = current < max_statuses
        message = ""
        if not allowed:
            message = self._get_limit_message('team_statuses', max_statuses)

        return LimitCheckResult(
            allowed=allowed,
            current=current,
            maximum=max_statuses,
            message=message
        )

    def can_create_personal_label(self) -> LimitCheckResult:
        from task_manager.labels.models import Label

        current = Label.objects.filter(
            creator=self.user,
            team__isnull=True
        ).count()
        max_labels = self.limits.max_personal_labels

        allowed = current < max_labels
        message = ""
        if not allowed:
            message = self._get_limit_message('personal_labels', max_labels)

        return LimitCheckResult(
            allowed=allowed,
            current=current,
            maximum=max_labels,
            message=message
        )

    def can_create_team_label(self, team) -> LimitCheckResult:
        from task_manager.labels.models import Label

        current = Label.objects.filter(team=team).count()
        max_labels = self.limits.max_team_labels

        allowed = current < max_labels
        message = ""
        if not allowed:
            message = self._get_limit_message('team_labels', max_labels)

        return LimitCheckResult(
            allowed=allowed,
            current=current,
            maximum=max_labels,
            message=message
        )

    def can_create_personal_note(self) -> LimitCheckResult:
        from task_manager.notes.models import Note

        current = Note.objects.filter(
            author=self.user,
            team__isnull=True
        ).count()
        max_notes = self.limits.max_personal_notes

        allowed = current < max_notes
        message = ""
        if not allowed:
            message = self._get_limit_message('personal_notes', max_notes)

        return LimitCheckResult(
            allowed=allowed,
            current=current,
            maximum=max_notes,
            message=message
        )

    def can_create_team_note(self, team) -> LimitCheckResult:
        from task_manager.notes.models import Note

        current = Note.objects.filter(team=team).count()
        max_notes = self.limits.max_team_notes

        allowed = current < max_notes
        message = ""
        if not allowed:
            message = self._get_limit_message('team_notes', max_notes)

        return LimitCheckResult(
            allowed=allowed,
            current=current,
            maximum=max_notes,
            message=message
        )

    def can_add_checklist_item(self, task) -> LimitCheckResult:
        current = task.checklist_items.count()
        max_items = self.limits.max_checklist_items

        allowed = current < max_items
        message = ""
        if not allowed:
            message = self._get_limit_message('checklist_items', max_items)

        return LimitCheckResult(
            allowed=allowed,
            current=current,
            maximum=max_items,
            message=message
        )

    def get_usage_summary(self) -> dict:
        """
        Get usage summary for UI display.

        Returns dict with keys: tasks, teams, statuses, labels, notes.
        Each value is {'current': int, 'max': int}.

        Note: Tasks are counted only where user is the author.
        This prevents double-counting when multiple users share a team.
        """
        from task_manager.tasks.models import Task
        from task_manager.teams.models import TeamMembership
        from task_manager.statuses.models import Status
        from task_manager.labels.models import Label
        from task_manager.notes.models import Note

        # Teams: count where user is admin
        teams_count = TeamMembership.objects.filter(
            user=self.user,
            role='admin'
        ).count()

        # Tasks: count only where user is author (personal + team)
        tasks_count = Task.objects.filter(author=self.user).count()

        # Personal statuses
        statuses_count = Status.objects.filter(
            creator=self.user,
            team__isnull=True
        ).count()

        # Personal labels
        labels_count = Label.objects.filter(
            creator=self.user,
            team__isnull=True
        ).count()

        # Personal notes
        notes_count = Note.objects.filter(
            author=self.user,
            team__isnull=True
        ).count()

        return {
            'tasks': {
                'current': tasks_count,
                'max': self.limits.max_tasks_total
            },
            'teams': {
                'current': teams_count,
                'max': self.limits.max_teams
            },
            'statuses': {
                'current': statuses_count,
                'max': self.limits.max_personal_statuses
            },
            'labels': {
                'current': labels_count,
                'max': self.limits.max_personal_labels
            },
            'notes': {
                'current': notes_count,
                'max': self.limits.max_personal_notes
            },
        }

    def get_team_usage_summary(self, team) -> dict:
        """
        Get usage summary for a specific team.

        Returns dict with keys: members, tasks, statuses, labels, notes.
        Each value is {'current': int, 'max': int, 'percent': int}.
        """
        from task_manager.tasks.models import Task
        from task_manager.statuses.models import Status
        from task_manager.labels.models import Label
        from task_manager.notes.models import Note

        def calc_percent(current, max_val):
            if max_val <= 0:
                return 0
            return min(int((current / max_val) * 100), 100)

        # Team members (active only)
        members_count = team.memberships.filter(status='active').count()

        # Tasks in team
        tasks_count = Task.objects.filter(team=team).count()

        # Team statuses
        statuses_count = Status.objects.filter(team=team).count()

        # Team labels
        labels_count = Label.objects.filter(team=team).count()

        # Team notes
        notes_count = Note.objects.filter(team=team).count()

        return {
            'members': {
                'current': members_count,
                'max': self.limits.max_team_members,
                'percent': calc_percent(
                    members_count, self.limits.max_team_members
                )
            },
            'tasks': {
                'current': tasks_count,
                'max': self.limits.max_tasks_total,
                'percent': calc_percent(
                    tasks_count, self.limits.max_tasks_total
                )
            },
            'statuses': {
                'current': statuses_count,
                'max': self.limits.max_team_statuses,
                'percent': calc_percent(
                    statuses_count, self.limits.max_team_statuses
                )
            },
            'labels': {
                'current': labels_count,
                'max': self.limits.max_team_labels,
                'percent': calc_percent(
                    labels_count, self.limits.max_team_labels
                )
            },
            'notes': {
                'current': notes_count,
                'max': self.limits.max_team_notes,
                'percent': calc_percent(
                    notes_count, self.limits.max_team_notes
                )
            },
        }
