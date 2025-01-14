from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    is_team_admin = models.BooleanField(default=False)
    team = models.ForeignKey(
        'teams.Team',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='team_members'
    )

    def user_str(self):
        return (
            f"{self.first_name} {self.last_name}"
            f"{'admin' if self.is_team_admin else ''}"
        )


# AbstractUser.__str__ = user_str
