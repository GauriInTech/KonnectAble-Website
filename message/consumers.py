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
            logger.debug("ChatConsumer: unauthenticated connect attempt")
            await self.close()
            return

        # verify conversation and membership
        conversation = await database_sync_to_async(self.get_conversation)()
        if conversation is None:
            logger.debug("ChatConsumer: user not participant of conversation %s", self.conversation_id)
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.debug("ChatConsumer: user %s connected to %s", user.pk, self.group_name)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.debug("ChatConsumer: disconnected %s (%s)", self.channel_name, close_code)

    async def receive_json(self, content, **kwargs):
        text = content.get('message')
        if not text:
            return

        user = self.scope['user']
        # persist message
        try:
            msg_data = await database_sync_to_async(self.create_message)(user, text)
        except Exception:
            logger.exception("ChatConsumer: failed to create message")
            return

        payload = {
            'type': 'chat.message',
            'message': msg_data['content'],
            'sender_id': msg_data['sender_id'],
            'sender_username': msg_data.get('sender_username', ''),
            'sender_avatar': msg_data.get('sender_avatar', ''),
            'message_id': msg_data['id'],
            'created_at': msg_data['created_at'],
            'conversation_id': self.conversation_id,
        }

        await self.channel_layer.group_send(self.group_name, payload)
        logger.debug("ChatConsumer: broadcast message %s in %s", msg.pk, self.group_name)

    async def chat_message(self, event):
        # send the message to WebSocket
        await self.send_json({
            'message': event['message'],
            'sender_id': event['sender_id'],
            'message_id': event['message_id'],
            'created_at': event['created_at'],
            'conversation_id': event['conversation_id'],
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
        # compute sender avatar URL safely
        avatar_url = ''
        try:
            profile = getattr(user, 'profile', None)
            if profile and getattr(profile, 'profile_image', None):
                avatar_url = profile.profile_image.url
        except Exception:
            avatar_url = ''

        sender_name = ''
        try:
            sender_name = user.get_full_name() or user.username
        except Exception:
            sender_name = getattr(user, 'username', '')

        return {
            'id': msg.pk,
            'content': msg.content,
            'created_at': msg.created_at.isoformat(),
            'sender_id': msg.sender_id,
            'sender_avatar': avatar_url,
            'sender_username': sender_name,
        }
