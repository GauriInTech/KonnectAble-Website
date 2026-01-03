import logging
import asyncio
import time
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

        # initialize typing debounce state
        self._last_typing_broadcast = 0
        self._typing_clear_task = None

        # ensure conversation exists and user is participant
        conversation = await database_sync_to_async(self.get_conversation)()
        if conversation is None:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # announce presence (online) to the group
        try:
            user_pk = getattr(user, 'pk', None)
            if user_pk:
                await self.channel_layer.group_send(self.group_name, {
                    'type': 'chat.presence',
                    'user_id': user_pk,
                    'status': 'online',
                })
        except Exception:
            logger.exception('ChatConsumer: failed to announce presence on connect')

        # Update undelivered messages to delivered
        await database_sync_to_async(self.update_undelivered_messages)()

        # Update all messages to seen for this user
        seen_ids = await database_sync_to_async(self.update_seen_messages)()

        # mark undelivered messages as delivered to this user and notify group (only for authenticated users)
        if not getattr(self, 'anonymous', False) and user and getattr(user, 'is_authenticated', False):
            try:
                delivered_ids = await database_sync_to_async(self.mark_messages_delivered)()
                for mid in delivered_ids:
                    # fetch sender id for the message so clients can decide who to show ticks to
                    sender_pk = await database_sync_to_async(lambda pk: Message.objects.filter(pk=pk).values_list('sender_id', flat=True).first())(mid)
                    await self.channel_layer.group_send(self.group_name, {
                        'type': 'chat.delivered',
                        'message_id': mid,
                        'user_id': user.pk,
                        'sender_id': sender_pk,
                        'status': 'delivered',
                    })
                for mid in seen_ids:
                    sender_pk = await database_sync_to_async(lambda pk: Message.objects.filter(pk=pk).values_list('sender_id', flat=True).first())(mid)
                    await self.channel_layer.group_send(self.group_name, {
                        'type': 'chat.read',
                        'message_id': mid,
                        'user_id': user.pk,
                        'sender_id': sender_pk,
                        'status': 'seen',
                    })
            except Exception:
                logger.exception('ChatConsumer: failed to mark delivered')

    async def disconnect(self, close_code):
        # announce presence (offline) to the group before leaving
        try:
            user = self.scope.get('user')
            user_pk = getattr(user, 'pk', None)
            if user_pk:
                await self.channel_layer.group_send(self.group_name, {
                    'type': 'chat.presence',
                    'user_id': user_pk,
                    'status': 'offline',
                })
            # prepare typing debounce state
            self._last_typing_broadcast = 0
            if getattr(self, '_typing_clear_task', None):
                try:
                    self._typing_clear_task.cancel()
                except Exception:
                    pass
            self._typing_clear_task = None
        except Exception:
            logger.exception('ChatConsumer: failed to announce presence on disconnect')

        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        # debug: log incoming payload for troubleshooting undefined/sending fallback
        logger.debug('ChatConsumer.receive_json payload: %r', content)

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
                'status': 'sent',
                'delivered_to': msg_data.get('delivered_to', []),
                'seen_by': msg_data.get('seen_by', []),
            }

            await self.channel_layer.group_send(self.group_name, payload)
            logger.debug("ChatConsumer: broadcast message %s in %s payload=%r", msg_data.get('id'), self.group_name, payload)
            return

        # typing indicator (client sends { typing: true/false })
        if 'typing' in content:
            try:
                is_typing = bool(content.get('typing'))
                user = self.scope.get('user')
                if not (user and getattr(user, 'is_authenticated', False)):
                    return

                now = time.time()
                # if explicit stop typing -> broadcast immediately and cancel clear task
                if not is_typing:
                    try:
                        await self.channel_layer.group_send(self.group_name, {
                            'type': 'chat.typing',
                            'user_id': user.pk,
                            'typing': False,
                        })
                    except Exception:
                        logger.exception('ChatConsumer: failed to broadcast typing=false')
                    # cancel pending clear task
                    if getattr(self, '_typing_clear_task', None):
                        try:
                            self._typing_clear_task.cancel()
                        except Exception:
                            pass
                        self._typing_clear_task = None
                    return

                # for is_typing == True, debounce broadcasts to at most once per second
                last = getattr(self, '_last_typing_broadcast', 0)
                if now - last > 1:
                    try:
                        await self.channel_layer.group_send(self.group_name, {
                            'type': 'chat.typing',
                            'user_id': user.pk,
                            'typing': True,
                        })
                        self._last_typing_broadcast = now
                    except Exception:
                        logger.exception('ChatConsumer: failed to broadcast typing')

                # schedule a clear after 3s of inactivity to send typing:false
                if getattr(self, '_typing_clear_task', None):
                    try:
                        self._typing_clear_task.cancel()
                    except Exception:
                        pass
                async def _clear_typing_after_delay():
                    try:
                        await asyncio.sleep(3)
                        await self.channel_layer.group_send(self.group_name, {
                            'type': 'chat.typing',
                            'user_id': user.pk,
                            'typing': False,
                        })
                        self._typing_clear_task = None
                    except asyncio.CancelledError:
                        return
                    except Exception:
                        logger.exception('ChatConsumer: clear typing task failed')

                self._typing_clear_task = asyncio.create_task(_clear_typing_after_delay())
            except Exception:
                logger.exception('ChatConsumer: failed to handle typing message')
            return

        # acknowledgements: seen/read receipts
        if content.get('ack') == 'seen' and content.get('message_id'):
            mid = content.get('message_id')
            user = self.scope['user']
            try:
                await database_sync_to_async(self.mark_message_seen)(mid, user)
                # include sender_id so clients can target tick updates to sender only
                sender_pk = await database_sync_to_async(lambda pk: Message.objects.filter(pk=pk).values_list('sender_id', flat=True).first())(mid)
                await self.channel_layer.group_send(self.group_name, {
                    'type': 'chat.read',
                    'message_id': mid,
                    'user_id': user.pk,
                    'sender_id': sender_pk,
                    'status': 'seen',
                })
            except Exception:
                logger.exception('ChatConsumer: failed to mark seen')
            return

        # no-op: other message types are handled above


    async def chat_message(self, event):
        logger.debug('ChatConsumer.chat_message event: %r', event)
        await self.send_json({
            'event': 'message',
            'message': event.get('message'),
            'sender_id': event.get('sender_id'),
            'message_id': event.get('message_id'),
            'created_at': event.get('created_at', ''),
            'conversation_id': event.get('conversation_id'),
            'sender_username': event.get('sender_username', ''),
            'sender_avatar': event.get('sender_avatar', ''),
            'status': event.get('status', 'sent'),
            'delivered_to': event.get('delivered_to', []),
            'seen_by': event.get('seen_by', []),
        })
        # mark this message as delivered and seen to this connected user (except sender)
        try:
            user = self.scope.get('user')
            sender_id = event.get('sender_id')
            msg_id = event.get('message_id')
            # only mark delivered and seen for authenticated users and when sender != recipient
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
                            'sender_id': sender_pk,
                            'status': 'delivered',
                        })
                    # mark as seen immediately when received
                    added_seen = await database_sync_to_async(self.mark_message_seen)(msg_id, user)
                    if added_seen:
                        # notify group that this message was read by this user
                        await self.channel_layer.group_send(self.group_name, {
                            'type': 'chat.read',
                            'message_id': msg_id,
                            'user_id': user.pk,
                            'sender_id': sender_pk,
                            'status': 'seen',
                        })
        except Exception:
            logger.exception('ChatConsumer: error marking delivered and seen in chat_message')

    async def chat_typing(self, event):
        """Forward typing indicator to WebSocket clients."""
        try:
            await self.send_json({
                'event': 'typing',
                'user_id': event.get('user_id'),
                'typing': event.get('typing', False),
            })
        except Exception:
            logger.exception('ChatConsumer: error sending typing event')

    async def chat_presence(self, event):
        """Forward presence updates (online/offline) to WebSocket clients."""
        try:
            await self.send_json({
                'event': 'presence',
                'user_id': event.get('user_id'),
                'status': event.get('status'),
            })
        except Exception:
            logger.exception('ChatConsumer: error sending presence event')

    async def chat_delivered(self, event):
        await self.send_json({
            'event': 'delivered',
            'message_id': event.get('message_id'),
            'user_id': event.get('user_id'),
            'sender_id': event.get('sender_id'),
            'status': event.get('status', 'delivered'),
        })

    async def chat_read(self, event):
        await self.send_json({
            'event': 'read',
            'message_id': event.get('message_id'),
            'user_id': event.get('user_id'),

            'sender_id': event.get('sender_id'),
            'status': event.get('status', 'seen'),

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
        # delegate to model method which is atomic and consistent
        try:
            return m.mark_seen(user)
        except Exception:
            logger.exception('mark_message_seen: model method failed')
            return False

    def mark_message_delivered(self, message_id, user):
        try:
            m = Message.objects.get(pk=message_id)
        except Message.DoesNotExist:
            return False
        try:
            return m.mark_delivered(user)
        except Exception:
            logger.exception('mark_message_delivered: model method failed')
            return False

    def update_undelivered_messages(self):
        """Mark all messages not sent by this user as delivered if they are still 'sent'"""
        user = self.scope.get('user')
        conv = Conversation.objects.get(pk=self.conversation_id)
        try:
            return Message.bulk_mark_delivered_for_user(conv, user)
        except Exception:
            logger.exception('update_undelivered_messages failed')
            return []

    def update_seen_messages(self):
        """Mark all messages not sent by this user as seen"""
        user = self.scope.get('user')
        conv = Conversation.objects.get(pk=self.conversation_id)
        try:
            return Message.bulk_mark_seen_for_user(conv, user)
        except Exception:
            logger.exception('update_seen_messages failed')
            return []

