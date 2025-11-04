from django.db import models
from task_manager.user.models import User
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _


class Status(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(
        max_length=24,
        unique=False,
        blank=False,
        verbose_name=_('Name'),
        validators=[
            RegexValidator(
                r'^[\w \-:,.!?]+$',
                message=_(
                    "Only letters, numbers, spaces, "
                    "and -_.,!? symbols are allowed. "
                    "Symbols <, >, #, & are not allowed."
                )
            ),
        ],
    )
    team = models.ForeignKey(
        'teams.Team',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='statuses'
    )
    creator = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        related_name='created_statuses',
        null=True,
        blank=True
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description'),)

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at')
    )

    # creating default statuses for user
    @classmethod
    def create_default_statuses_for_user(cls, user):
        """Создает дефолтные статусы для нового пользователя"""
        default_statuses = [
            {
                'name': _("To Do"),
                'description': _("Task has been created but not yet started")
            },
            {
                'name': _("In Progress"),
                'description': _("Task is currently being worked on")
            },
            {
                'name': _("On Hold"),
                'description': _("Task is temporarily paused")
            },
            {
                'name': _("Completed"),
                'description': _("Task has been finished successfully")
            },
            {
                'name': _("Cancelled"),
                'description': _("Task was abandoned or deemed unnecessary")
            },
            {
                'name': _("Blocked"),
                'description': _(
                    "Task cannot proceed due to external dependencies"
                )
            },
        ]

        created_statuses = []
        for status_data in default_statuses:
            status = cls.objects.create(
                name=status_data['name'],
                description=status_data['description'],
                creator=user
            )
            created_statuses.append(status)

        return created_statuses

    def __str__(self):
        return self.name
