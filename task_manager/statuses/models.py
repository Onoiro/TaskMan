from django.db import models
from task_manager.user.models import User
from django.core.validators import MinLengthValidator, RegexValidator


class Status(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(
        max_length=150,
        unique=True,
        blank=False,
        validators=[RegexValidator('^[a-zA-Z0-9]'), MinLengthValidator(2)]
    )
    creator = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='created_statuses'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
