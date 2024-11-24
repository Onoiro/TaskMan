from django.contrib.auth.models import User
from django.db import models


def is_team_admin(self):
    is_team_admin = models.BooleanField(default=False)
    return self.is_team_admin
 
def user_str(self):
    return f"{self.first_name} {self.last_name} {'admin' if self.is_team_admin else ''}"


User.__str__ = user_str
