import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Conversation, Message
from django.utils import timezone

logger = logging.getLogger(__name__)

User = get_user_model()


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs'].get('conversation_id')
        self.group_name = f"chat_{self.conversation_id}"

        user = self.scope.get('user')
        if user is None or not user.is_authenticated:
            await self.close()
            return

        conversation = await database_sync_to_async(self.get_conversation)()
        if conversation is None:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Update undelivered messages to delivered
        await database_sync_to_async(self.update_undelivered_messages)()

        # Update all messages to seen for this user
        await database_sync_to_async(self.update_seen_messages)()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        text = content.get('message')
        if not text:
            return

        user = self.scope['user']
        msg_data = await database_sync_to_async(self.create_message)(user, text)

        payload = {
            'type': 'chat.message',
            'message': msg_data['content'],
            'sender_id': msg_data['sender_id'],
            'sender_username': msg_data.get('sender_username', ''),
            'sender_avatar': msg_data.get('sender_avatar', ''),
            'message_id': msg_data['id'],
            'created_at': msg_data['created_at'],
            'conversation_id': self.conversation_id,
            'status': msg_data['status'],
        }

        await self.channel_layer.group_send(self.group_name, payload)

    async def chat_message(self, event):
        await self.send_json({
            'message': event.get('message'),
            'sender_id': event.get('sender_id'),
            'message_id': event.get('message_id'),
            'created_at': event.get('created_at'),
            'conversation_id': event.get('conversation_id'),
            'sender_username': event.get('sender_username', ''),
            'sender_avatar': event.get('sender_avatar', ''),
            'status': event.get('status', 'sent'),
        })

    def get_conversation(self):
        try:
            conv = Conversation.objects.get(pk=self.conversation_id)
        except Conversation.DoesNotExist:
            return None
        user = self.scope.get('user')
        if conv.participants.filter(pk=user.pk).exists():
            return conv
        return None

    def create_message(self, user, text):
        conv = Conversation.objects.get(pk=self.conversation_id)
        msg = Message.objects.create(conversation=conv, sender=user, content=text, created_at=timezone.now())

        avatar_url = ''
        try:
            profile = getattr(user, 'profile', None)
            if profile and getattr(profile, 'profile_image', None):
                avatar_url = profile.profile_image.url
        except Exception:
            avatar_url = ''

        sender_name = user.get_full_name() or user.username

        return {
            'id': msg.pk,
            'content': msg.content,
            'created_at': msg.created_at.isoformat(),
            'sender_id': msg.sender_id,
            'sender_avatar': avatar_url,
            'sender_username': sender_name,
            'status': msg.status
        }

    def update_undelivered_messages(self):
        """Mark all messages not sent by this user as delivered if they are still 'sent'"""
        user = self.scope.get('user')
        conv = Conversation.objects.get(pk=self.conversation_id)
        undelivered = conv.messages.exclude(sender=user).filter(status='sent')
        for msg in undelivered:
            msg.status = 'delivered'
            msg.save()

    def update_seen_messages(self):
        """Mark all messages not sent by this user as seen"""
        user = self.scope.get('user')
        conv = Conversation.objects.get(pk=self.conversation_id)
        unseen = conv.messages.exclude(sender=user).filter(status__in=['sent', 'delivered'])
        for msg in unseen:
            msg.status = 'seen'
            msg.save()
