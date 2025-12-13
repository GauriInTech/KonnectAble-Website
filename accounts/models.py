# Create your models here.

from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    Custom user model that extends Django's AbstractUser.
    We add an `is_differently_abled` flag and optional phone field.
    """
    is_differently_abled = models.BooleanField("Differently abled", default=False)
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        # show full name if available else username
        return self.get_full_name() or self.username
