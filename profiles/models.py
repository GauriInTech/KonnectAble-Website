

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
    location = models.CharField(blank=True, max_length=255, default='')
    portfolio_url = models.URLField(blank=True, null=True)
    skills = models.CharField(blank=True, null=True, help_text='Comma-separated skills', max_length=512)
    connections = models.ManyToManyField('self', blank=True, symmetrical=False, related_name='connected_to')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.user)

    # convenience helpers for support (follow) behavior
    def supports_count(self):
        """Number of profiles this profile supports (following)."""
        return self.connections.count()

    def supporters_count(self):
        """Number of profiles that support this profile (followers)."""
        return self.connected_to.count()

    def get_supporting(self):
        """Queryset of profiles this profile is supporting."""
        return self.connections.all()

    def get_supporters(self):
        """Queryset of profiles that support this profile."""
        return self.connected_to.all()

    def is_supported_by(self, other_profile):
        """Return True if other_profile supports this profile."""
        return self in other_profile.connections.all()

    def toggle_support(self, other_profile):
        """Toggle support from this profile to other_profile.

        Returns True if support was added, False if removed.
        """
        if other_profile in self.connections.all():
            self.connections.remove(other_profile)
            return False
        else:
            self.connections.add(other_profile)
            return True

