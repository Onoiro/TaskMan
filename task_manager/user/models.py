from django.db import models
from django.forms import ModelForm
from django.core.validators import MinLengthValidator, \
                                   RegexValidator

class User(models.Model):
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=150, unique=True, blank=False,
                                validators=[RegexValidator(
                                '^[a-zA-Z0-9.@_+-]+$')])
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    password = models.CharField(max_length=100, blank=False,
                                validators=[MinLengthValidator(3)]
                                )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user_name

    def get_edit_url(self):
        return "/users/{}/edit".format(self.id)

    def get_delete_url(self):
        return "/users/{}/delete".format(self.id)


class UserForm(ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'password']
