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
        # debug: log auth status and relevant headers to help diagnose handshake issues
        try:
            cookie_header = None
            origin_header = None
            for h, v in self.scope.get('headers', []):
                hn = h.decode('utf-8', errors='ignore')
                if hn.lower() == 'cookie':
                    cookie_header = v.decode('utf-8', errors='ignore')
                if hn.lower() == 'origin':
                    origin_header = v.decode('utf-8', errors='ignore')
            logger.debug('ChatConsumer.connect: user=%s authenticated=%s conversation=%s origin=%s cookie=%s',
                         getattr(user, 'pk', None), bool(user and getattr(user, 'is_authenticated', False)),
                         self.conversation_id, origin_header, ('<present>' if cookie_header else '<none>'))
        except Exception:
            logger.exception('ChatConsumer: error logging connect headers')

        # determine if client is anonymous; if so allow for connectivity testing
        anonymous = not (user and getattr(user, 'is_authenticated', False))
        self.anonymous = anonymous
        if anonymous:
            logger.debug('ChatConsumer: anonymous connect allowed for testing (conversation=%s)', self.conversation_id)
        else:
            # verify conversation and membership for authenticated users only
            conversation = await database_sync_to_async(self.get_conversation)()
            if conversation is None:
                logger.debug("ChatConsumer: user not participant of conversation %s", self.conversation_id)
                await self.close()
                return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.debug("ChatConsumer: user %s connected to %s", user.pk, self.group_name)

        # mark undelivered messages as delivered to this user and notify group (only for authenticated users)
        if not getattr(self, 'anonymous', False) and user and getattr(user, 'is_authenticated', False):
            try:
                delivered_ids = await database_sync_to_async(self.mark_messages_delivered)()
                for mid in delivered_ids:
                    await self.channel_layer.group_send(self.group_name, {
                        'type': 'chat.delivered',
                        'message_id': mid,
                        'user_id': user.pk,
                    })
            except Exception:
                logger.exception('ChatConsumer: failed to mark delivered')

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.debug("ChatConsumer: disconnected %s (%s)", self.channel_name, close_code)

    async def receive_json(self, content, **kwargs):
        # handle incoming message send or acknowledgements
        if 'message' in content:
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
                'delivered_to': msg_data.get('delivered_to', []),
                'seen_by': msg_data.get('seen_by', []),
            }

            await self.channel_layer.group_send(self.group_name, payload)
            logger.debug("ChatConsumer: broadcast message %s in %s", msg_data.get('id'), self.group_name)
            return

        # acknowledgements: seen/read receipts
        if content.get('ack') == 'seen' and content.get('message_id'):
            mid = content.get('message_id')
            user = self.scope['user']
            try:
                await database_sync_to_async(self.mark_message_seen)(mid, user)
                await self.channel_layer.group_send(self.group_name, {
                    'type': 'chat.read',
                    'message_id': mid,
                    'user_id': user.pk,
                })
            except Exception:
                logger.exception('ChatConsumer: failed to mark seen')
            return

        # no-op: other message types are handled above

    async def chat_message(self, event):
        # send the message to WebSocket
        await self.send_json({
            'event': 'message',
            'message': event.get('message'),
            'sender_id': event.get('sender_id'),
            'message_id': event.get('message_id'),
            'created_at': event.get('created_at'),
            'conversation_id': event.get('conversation_id'),
            'sender_username': event.get('sender_username', ''),
            'sender_avatar': event.get('sender_avatar', ''),
            'delivered_to': event.get('delivered_to', []),
            'seen_by': event.get('seen_by', []),
        })
        # mark this message as delivered to this connected user (except sender)
        try:
            user = self.scope.get('user')
            sender_id = event.get('sender_id')
            msg_id = event.get('message_id')
            # only mark delivered for authenticated users and when sender != recipient
            if user and getattr(user, 'is_authenticated', False) and sender_id and msg_id:
                try:
                    sender_pk = int(sender_id)
                except Exception:
                    sender_pk = None
                try:
                    user_pk = int(getattr(user, 'pk', 0) or 0)
                except Exception:
                    user_pk = 0
                if sender_pk and msg_id and sender_pk != user_pk:
                    added = await database_sync_to_async(self.mark_message_delivered)(msg_id, user)
                    if added:
                        # notify group that this message was delivered to this user
                        await self.channel_layer.group_send(self.group_name, {
                            'type': 'chat.delivered',
                            'message_id': msg_id,
                            'user_id': user.pk,
                        })
        except Exception:
            logger.exception('ChatConsumer: error marking delivered in chat_message')

    async def chat_delivered(self, event):
        await self.send_json({
            'event': 'delivered',
            'message_id': event.get('message_id'),
            'user_id': event.get('user_id'),
        })

    async def chat_read(self, event):
        await self.send_json({
            'event': 'read',
            'message_id': event.get('message_id'),
            'user_id': event.get('user_id'),
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
        # Do not mark as delivered immediately - wait for recipients to connect/receive
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
            'delivered_to': [],
            'seen_by': [],
        }

    def mark_messages_delivered(self):
        # mark all messages in this conversation not sent by this connecting user as delivered to them
        user = self.scope.get('user')
        conv = Conversation.objects.get(pk=self.conversation_id)
        msgs = conv.messages.exclude(sender=user).exclude(delivered_to=user)
        ids = []
        for m in msgs:
            m.delivered_to.add(user)
            ids.append(m.pk)
        return ids

    def mark_message_seen(self, message_id, user):
        try:
            m = Message.objects.get(pk=message_id)
        except Message.DoesNotExist:
            return False
        if m.seen_by.filter(pk=user.pk).exists():
            return False
        m.seen_by.add(user)
        return True

    def mark_message_delivered(self, message_id, user):
        try:
            m = Message.objects.get(pk=message_id)
        except Message.DoesNotExist:
            return False
        if m.delivered_to.filter(pk=user.pk).exists():
            return False
        m.delivered_to.add(user)
        return True
