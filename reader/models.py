from django.db import models

# Create your models here.


class User(models.Model):

    user_id = models.IntegerField(auto_created=True, primary_key=True)
    email = models.CharField(max_length=100, null=False)
    borrow_num = models.IntegerField(default=0)
    user_name = models.CharField(max_length=20, null=False, unique=True)
    password = models.CharField(max_length=20, null=False)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.user_name
