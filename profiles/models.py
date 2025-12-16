

from django.db import models
from django.conf import settings

class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    bio = models.TextField(blank=True)
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)
    headline = models.CharField(blank=True, null=True, max_length=255)
    location = models.CharField(blank=True, max_length=255)
    portfolio_url = models.URLField(blank=True)
    skills = models.CharField(blank=True, help_text='Comma-separated skills', max_length=512)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.user)

