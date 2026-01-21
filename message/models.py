from django.db import models
from django.utils import timezone
from accounts.models import User
import uuid


class Conversation(models.Model):
    """
    Represents a one-to-one conversation between two users.
    This is the container for all messages between them.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participant1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations_as_participant1')
    participant2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations_as_participant2')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message = models.ForeignKey('Message', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

    class Meta:
        unique_together = ('participant1', 'participant2')
        indexes = [
            models.Index(fields=['participant1', 'updated_at']),
            models.Index(fields=['participant2', 'updated_at']),
            models.Index(fields=['updated_at']),
        ]

    def get_other_user(self, user):
        """Get the other participant in the conversation"""
        return self.participant2 if self.participant1 == user else self.participant1

    def __str__(self):
        return f"Conversation between {self.participant1.username} and {self.participant2.username}"


class Message(models.Model):
    """
    Represents a single message in a conversation.
    Includes read receipt tracking and support for multiple message types.
    """
    MESSAGE_TYPE_CHOICES = [
        ('text', 'Text Message'),
        ('image', 'Image'),
        ('file', 'File'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField(blank=True)
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default='text')
    
    # Media fields
    image = models.ImageField(upload_to='messages/images/', null=True, blank=True)
    file = models.FileField(upload_to='messages/files/', null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    
    # Read receipt
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
            models.Index(fields=['is_read']),
        ]

    def mark_as_read(self):
        """Mark message as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    def __str__(self):
        return f"Message from {self.sender.username} at {self.created_at}"


class Call(models.Model):
    """
    Represents a call between two users in a conversation.
    Tracks call duration, status, and type.
    """
    CALL_STATUS_CHOICES = [
        ('initiated', 'Initiated'),
        ('ringing', 'Ringing'),
        ('answered', 'Answered'),
        ('ended', 'Ended'),
        ('missed', 'Missed'),
        ('declined', 'Declined'),
    ]

    CALL_TYPE_CHOICES = [
        ('audio', 'Audio Call'),
        ('video', 'Video Call'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='calls')
    initiator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='initiated_calls')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_calls')
    call_type = models.CharField(max_length=20, choices=CALL_TYPE_CHOICES, default='audio')
    status = models.CharField(max_length=20, choices=CALL_STATUS_CHOICES, default='initiated')
    
    # Timestamps
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    initiated_at = models.DateTimeField(auto_now_add=True)
    ringing_until = models.DateTimeField(null=True, blank=True)  # Auto-decline after this time
    
    # Duration in seconds
    duration = models.IntegerField(default=0)
    
    # WebRTC Signaling
    webrtc_offer = models.JSONField(null=True, blank=True)  # Store SDP offer
    webrtc_answer = models.JSONField(null=True, blank=True)  # Store SDP answer
    ice_candidates = models.JSONField(default=list, blank=True)  # Store ICE candidates
    
    # Call attempt tracking
    is_answered = models.BooleanField(default=False)  # Whether call was ever answered
    is_missed = models.BooleanField(default=False)  # Whether call expired without answer

    class Meta:
        ordering = ['-initiated_at']
        indexes = [
            models.Index(fields=['conversation', 'initiated_at']),
            models.Index(fields=['initiator', 'initiated_at']),
            models.Index(fields=['receiver', 'initiated_at']),
        ]

    def __str__(self):
        return f"{self.get_call_type_display()} from {self.initiator.username} to {self.receiver.username}"


class Typing(models.Model):
    """
    Represents typing status in a conversation.
    This is for real-time typing indicators.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='typing_statuses')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='typing_statuses')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('conversation', 'user')

    def __str__(self):
        return f"{self.user.username} is typing in conversation {self.conversation.id}"
