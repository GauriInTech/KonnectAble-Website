from django.conf import settings
from django.db import models
from django.utils import timezone


# Conversations group two or more users; messages belong to a conversation.
class Conversation(models.Model):
	participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="conversations")
	created_at = models.DateTimeField(default=timezone.now)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"Conversation {self.pk} ({self.participants.count()} participants)"


class Message(models.Model):
	conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
	sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
	content = models.TextField(blank=True)
	created_at = models.DateTimeField(default=timezone.now, db_index=True)
	# status: 'sent' -> saved by sender, 'delivered' -> received by recipient device, 'read' -> opened/read by recipient
	STATUS_SENT = 'sent'
	STATUS_DELIVERED = 'delivered'
	STATUS_READ = 'read'

	STATUS_CHOICES = [
		(STATUS_SENT, 'Sent'),
		(STATUS_DELIVERED, 'Delivered'),
		(STATUS_READ, 'Read'),
	]

	status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_SENT, db_index=True)
	is_read = models.BooleanField(default=False)

	class Meta:
		ordering = ("created_at",)

	def __str__(self):
		return f"Message {self.pk} from {self.sender}" 
