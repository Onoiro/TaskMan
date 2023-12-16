from django.db import models

class User(models.Model):
    ID = models.AutoField(primary_key=True)
    user_name = models.CharField(max_length=100)
    fullname = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def get_edit_url(self):
        return "/users/{}/edit".format(self.ID)

    def get_delete_url(self):
        return "/users/{}/delete".format(self.ID)
