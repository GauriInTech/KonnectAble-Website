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
        # Mark messages as read for the user
        read_message_ids = await database_sync_to_async(self.mark_messages_read)(user)
        if read_message_ids:
            # Broadcast read receipts to other participants (per-message to ensure handlers run)
            for mid in read_message_ids:
                logger.debug("ChatConsumer: broadcasting read status for message %s in %s by user %s", mid, self.group_name, user.pk)
                await self.channel_layer.group_send(self.group_name, {
                    'type': 'message.status',
                    'message_id': mid,
                    'status': 'read',
                    'reader_id': user.pk,
                })
        logger.debug("ChatConsumer: user %s connected to %s", user.pk, self.group_name)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.debug("ChatConsumer: disconnected %s (%s)", self.channel_name, close_code)

    async def receive_json(self, content, **kwargs):
        # support two actions: sending a message or marking messages as read
        action = content.get('action')
        user = self.scope['user']
        logger.debug("ChatConsumer.receive_json: action=%s from user=%s content=%s", action, getattr(user, 'pk', None), content)

        # Delivered ack from recipient device
        if action == 'delivered':
            msg_id = content.get('message_id')
            if not msg_id:
                return
            try:
                updated = await database_sync_to_async(self.mark_message_delivered)(msg_id)
            except Exception:
                logger.exception("ChatConsumer: failed to mark message delivered")
                return

            if updated:
                # notify group about status change
                await self.channel_layer.group_send(self.group_name, {
                    'type': 'message.status',
                    'message_id': msg_id,
                    'status': 'delivered',
                })
            return

        if action == 'read':
            # client notifies which message ids were read
            msg_ids = content.get('message_ids') or []
            if not msg_ids:
                return
            try:
                read_ids = await database_sync_to_async(self.mark_specific_messages_read)(user, msg_ids)
            except Exception:
                logger.exception("ChatConsumer: failed to mark messages read")
                return

            if read_ids:
                for mid in read_ids:
                    logger.debug("ChatConsumer: user %s marked message %s read in %s", user.pk, mid, self.group_name)
                    await self.channel_layer.group_send(self.group_name, {
                        'type': 'message.status',
                        'message_id': mid,
                        'status': 'read',
                        'reader_id': user.pk,
                    })
            return

        if action == 'typing':
            # Broadcast typing status to group
            is_typing = bool(content.get('is_typing', True))
            await self.channel_layer.group_send(self.group_name, {
                'type': 'user.typing',
                'user_id': user.pk,
                'is_typing': is_typing,
            })
            return

        # default: treat as sending a message
        text = content.get('message')
        if not text:
            return

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
            'status': msg_data.get('status', 'sent'),
        }

        await self.channel_layer.group_send(self.group_name, payload)
        logger.debug("ChatConsumer: broadcast message %s in %s", msg_data.get('id'), self.group_name)

    async def user_typing(self, event):
        # send typing events to websocket clients
        await self.send_json({
            'type': 'user_typing',
            'user_id': event.get('user_id'),
            'is_typing': event.get('is_typing', False),
        })

    async def chat_message(self, event):
        # send the message to WebSocket
        await self.send_json({
            'type': 'chat_message',
            'message': event['message'],
            'sender_id': event['sender_id'],
            'sender_username': event.get('sender_username', ''),
            'sender_avatar': event.get('sender_avatar', ''),
            'message_id': event['message_id'],
            'created_at': event['created_at'],
            'conversation_id': event['conversation_id'],
            'status': event.get('status', 'sent'),
        })

    async def messages_read(self, event):
        # send read receipts to WebSocket
        # convert to per-message status updates so clients can update ticks
        for mid in event.get('read_message_ids', []):
            await self.send_json({
                'type': 'message_status',
                'message_id': mid,
                'status': 'read',
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

    def mark_messages_read(self, user):
        # Mark all unread messages in this conversation as read for the user
        messages_to_read = Message.objects.filter(
            conversation_id=self.conversation_id
        ).exclude(sender=user).filter(is_read=False)
        message_ids = list(messages_to_read.values_list('id', flat=True))
        if message_ids:
            messages_to_read.update(is_read=True, status=Message.STATUS_READ)
        return message_ids

    def mark_specific_messages_read(self, user, message_ids):
        # Only mark messages that belong to this conversation and are unread
        msgs = Message.objects.filter(conversation_id=self.conversation_id, pk__in=message_ids).exclude(sender=user).filter(is_read=False)
        ids = list(msgs.values_list('id', flat=True))
        if ids:
            msgs.update(is_read=True, status=Message.STATUS_READ)
        return ids

    def create_message(self, user, text):
        conv = Conversation.objects.get(pk=self.conversation_id)
        msg = Message.objects.create(conversation=conv, sender=user, content=text, created_at=timezone.now(), status=Message.STATUS_SENT)
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
            'status': msg.status,
        }

    def mark_message_delivered(self, msg_id):
        try:
            msg = Message.objects.get(pk=msg_id)
        except Message.DoesNotExist:
            return False
        if msg.status == Message.STATUS_SENT:
            msg.status = Message.STATUS_DELIVERED
            msg.save(update_fields=['status'])
            return True
        return False

    async def message_status(self, event):
        # forward status updates to websocket clients
        await self.send_json({
            'type': 'message_status',
            'message_id': event.get('message_id'),
            'status': event.get('status'),
        })
