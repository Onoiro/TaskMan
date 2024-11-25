from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    is_team_admin = models.BooleanField(default=False)

 
    def user_str(self):
        return f"{self.first_name} {self.last_name} {'admin' if self.is_team_admin else ''}"


# AbstractUser.__str__ = user_str
