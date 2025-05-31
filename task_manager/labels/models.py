from django.db import models
from task_manager.user.models import User


class Label(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(
        max_length=100,
        unique=True,
    )
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_labels'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
