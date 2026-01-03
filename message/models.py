from django.conf import settings
from django.db import models
from django.utils import timezone


# Conversations group two or more users; messages belong to a conversation.
class Conversation(models.Model):
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="conversations"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_conversations",
        null=True,
        blank=True
    )
    name = models.CharField(max_length=255, blank=True, null=True)
    admins = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="admin_conversations",
        blank=True
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.name:
            return f"Conversation {self.pk}: {self.name} ({self.participants.count()} participants)"
        return f"Conversation {self.pk} ({self.participants.count()} participants)"

    @classmethod
    def get_or_create_for_users(cls, user_qs_or_ids, created_by=None):
        """Find an existing conversation matching exactly the provided users (by id or queryset).

        If not found, create a new Conversation with those participants and optionally set `created_by`.
        Returns (conversation, created_bool).
        """
        from django.db.models import Count
        # normalize to set of ints
        if hasattr(user_qs_or_ids, 'values_list'):
            ids = set(int(x) for x in user_qs_or_ids.values_list('pk', flat=True))
        else:
            ids = set(int(x) for x in list(user_qs_or_ids))

        if created_by is not None:
            ids.add(int(created_by.pk if hasattr(created_by, 'pk') else created_by))

        # find candidates with same participant count and overlapping ids
        candidates = cls.objects.annotate(num_parts=Count('participants')).filter(num_parts=len(ids))
        candidates = candidates.filter(participants__pk__in=ids).distinct()

        for c in candidates:
            part_ids = set(c.participants.values_list('pk', flat=True))
            if part_ids == ids:
                return c, False

        # create new conversation
        conv = cls.objects.create(created_by=(created_by.pk if created_by is not None else None))
        conv.participants.add(*list(ids))
        if created_by is not None:
            try:
                conv.admins.add(created_by)
            except Exception:
                pass
        return conv, True


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages"
    )
    content = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    is_read = models.BooleanField(default=False)
    # per-user delivery/seen tracking
    delivered_to = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='delivered_messages',
        blank=True
    )
    seen_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='seen_messages',
        blank=True
    )

    # ✅ ADDED FOR WHATSAPP-LIKE TICKS
    STATUS_CHOICES = (
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('seen', 'Seen'),
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='sent'
    )
    # ✅ END ADDITION

    class Meta:
        ordering = ("created_at",)

    def __str__(self):
        return f"Message {self.pk} from {self.sender}"

    def mark_delivered(self, user):
        """Mark this message as delivered to a specific user.

        Returns True if the delivered state changed for this user.
        This method keeps `status` in sync and is safe to call repeatedly.
        """
        from django.db import transaction

        if self.delivered_to.filter(pk=user.pk).exists():
            return False
        with transaction.atomic():
            # add m2m entry
            self.delivered_to.add(user)
            if self.status == 'sent':
                self.status = 'delivered'
                # only update status to reduce unnecessary writes
                self.save(update_fields=['status'])
        return True

    def mark_seen(self, user):
        """Mark this message as seen by a specific user.

        Returns True if seen state changed for this user. Keeps `status` and `is_read` in sync.
        """
        from django.db import transaction

        if self.seen_by.filter(pk=user.pk).exists():
            return False
        with transaction.atomic():
            self.seen_by.add(user)
            # ensure status/is_read reflect seen
            self.status = 'seen'
            self.is_read = True
            self.save(update_fields=['status', 'is_read'])
        return True

    @classmethod
    def bulk_mark_delivered_for_user(cls, conversation, user):
        """Mark all messages in `conversation` as delivered to `user` where applicable.

        Returns list of message ids that were changed.
        """
        from django.db import transaction

        msgs = conversation.messages.exclude(sender=user).exclude(delivered_to=user).filter(status='sent')
        changed = []
        with transaction.atomic():
            for m in msgs.select_for_update():
                m.delivered_to.add(user)
                if m.status == 'sent':
                    m.status = 'delivered'
                    m.save(update_fields=['status'])
                changed.append(m.pk)
        return changed

    @classmethod
    def bulk_mark_seen_for_user(cls, conversation, user):
        """Mark all messages in `conversation` as seen by `user` where applicable.

        Returns list of message ids that were changed.
        """
        from django.db import transaction

        msgs = conversation.messages.exclude(sender=user).exclude(seen_by=user).filter(status__in=['sent', 'delivered'])
        changed = []
        with transaction.atomic():
            for m in msgs.select_for_update():
                m.seen_by.add(user)
                m.status = 'seen'
                m.is_read = True
                m.save(update_fields=['status', 'is_read'])
                changed.append(m.pk)
        return changed
