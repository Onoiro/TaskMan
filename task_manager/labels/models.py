from django.db import models


class Label(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(
        max_length=100,
        unique=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

