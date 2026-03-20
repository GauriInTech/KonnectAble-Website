from django.conf import settings
from django.db import models
from django.utils import timezone


# Conversations group two or more users; messages belong to a conversation.
class Conversation(models.Model):
	participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="conversations")
	created_at = models.DateTimeField(default=timezone.now)
	updated_at = models.DateTimeField(auto_now=True)
	
	# Group-specific fields
	is_group = models.BooleanField(default=False)
	name = models.CharField(max_length=100, blank=True, null=True)
	description = models.TextField(blank=True, null=True)
	admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="administered_groups")
	group_image = models.ImageField(upload_to='group_images/', blank=True, null=True)

	def __str__(self):
		if self.is_group:
			return f"Group: {self.name or f'Group {self.pk}'}"
		return f"Conversation {self.pk} ({self.participants.count()} participants)"
	
	def get_last_message(self):
		return self.messages.order_by('-created_at').first()
	
	def get_last_message_preview(self):
		msg = self.get_last_message()
		if msg:
			preview = msg.content[:50]
			if len(msg.content) > 50:
				preview += "..."
			if msg.is_edited:
				preview = f"(edited) {preview}"
			return preview
		return "No messages yet"


class Message(models.Model):
	conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
	sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
	content = models.TextField(blank=True)
	created_at = models.DateTimeField(default=timezone.now, db_index=True)
	updated_at = models.DateTimeField(auto_now=True)
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
	is_edited = models.BooleanField(default=False)
	is_deleted = models.BooleanField(default=False)
	is_pinned = models.BooleanField(default=False)

	class Meta:
		ordering = ("created_at",)

	def __str__(self):
		return f"Message {self.pk} from {self.sender}"


class MessageReaction(models.Model):
	"""Emoji reactions to messages"""
	message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="reactions")
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	emoji = models.CharField(max_length=10)
	created_at = models.DateTimeField(default=timezone.now)

	class Meta:
		unique_together = ('message', 'user', 'emoji')
		ordering = ['created_at']

	def __str__(self):
		return f"{self.emoji} on message {self.message.pk} by {self.user}"


class UserOnlineStatus(models.Model):
	"""Track user online/offline status"""
	user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="online_status")
	is_online = models.BooleanField(default=False)
	last_seen = models.DateTimeField(default=timezone.now)

	def __str__(self):
		return f"{self.user.username} - {'Online' if self.is_online else 'Offline'}" 
