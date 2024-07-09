from django.contrib.auth.models import User


def user_str(self):
    return f"{self.first_name} {self.last_name}"


User.__str__ = user_str
