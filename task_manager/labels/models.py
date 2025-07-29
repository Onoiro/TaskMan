from django.db import models
from task_manager.user.models import User
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _


class Label(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(
        max_length=24,
        unique=False,
        validators=[
            RegexValidator(
                r'^[\w \-:,.!?]+$',
                message=_(
                    "Only letters, numbers, spaces, "
                    "and -_.,!? symbols are allowed. "
                    "Symbols <, >, #, & are not allowed"
                )
            ),
        ],
    )
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_labels'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
