from django import template

register = template.Library()


@register.filter
def avatar_url(user):
    """Return profile image URL for a user or empty string if not available."""
    if user is None:
        return ''
    try:
        profile = getattr(user, 'profile', None)
        if profile and getattr(profile, 'profile_image', None):
            return profile.profile_image.url
    except Exception:
        return ''
    return ''
