from django.db import models
from django.conf import settings

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('support', 'Support'),
        ('job_application', 'Job Application'),
        ('job_accepted', 'Job Accepted'),
        ('job_rejected', 'Job Rejected'),
    )

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # Optional: link to related object (job application, etc.)
    related_job = models.ForeignKey('jobPanel.Job', on_delete=models.CASCADE, null=True, blank=True)
    related_application = models.ForeignKey('jobPanel.Application', on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.sender.username} -> {self.recipient.username}: {self.notification_type}"
