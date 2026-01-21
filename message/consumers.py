import json
import logging
import asyncio
from datetime import timedelta
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from accounts.models import User
from .models import Conversation, Message, Typing, Call

logger = logging.getLogger(__name__)

# Call timeout configuration (30 seconds)
CALL_TIMEOUT_SECONDS = 30


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time messaging and typing indicators.
    Handles message sending, typing status, and call notifications.
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.room_name = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.room_name}'
        self.user = self.scope['user']
        self.call_timeout_task = None  # Track call timeout task
        
        # Only allow authenticated users
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Verify user is part of this conversation
        has_access = await self.verify_conversation_access()
        if not has_access:
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Broadcast user online status
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status',
                'user_id': self.user.id,
                'username': self.user.username,
                'status': 'online',
            }
        )
        
        logger.info(f"User {self.user.username} connected to conversation {self.room_name}")
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        # Cancel any pending call timeout
        if self.call_timeout_task:
            self.call_timeout_task.cancel()
        
        # Broadcast user offline status
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status',
                'user_id': self.user.id,
                'username': self.user.username,
                'status': 'offline',
            }
        )
        
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        # Remove typing status
        await self.remove_typing_status()
        logger.info(f"User {self.user.username} disconnected from conversation {self.room_name}")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'message':
                await self.handle_message(data)
            elif message_type == 'typing':
                await self.handle_typing(data)
            elif message_type == 'call':
                await self.handle_call(data)
            elif message_type == 'webrtc_offer':
                await self.handle_webrtc_offer(data)
            elif message_type == 'webrtc_answer':
                await self.handle_webrtc_answer(data)
            elif message_type == 'ice_candidate':
                await self.handle_ice_candidate(data)
            elif message_type == 'read_receipt':
                await self.handle_read_receipt(data)
        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
            await self.send_error("Invalid message format")
    
    async def handle_message(self, data):
        """Handle new message"""
        try:
            content = data.get('content', '').strip()
            
            if not content:
                await self.send_error("Message cannot be empty")
                return
            
            # Save message to database
            message = await self.save_message(content)
            
            # Remove typing status when message is sent
            await self.remove_typing_status()
            
            # Broadcast message to room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message_id': str(message.id),
                    'sender': message.sender.username,
                    'sender_id': message.sender.id,
                    'content': message.content,
                    'created_at': message.created_at.isoformat(),
                    'is_read': message.is_read,
                }
            )
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await self.send_error(f"Error sending message: {str(e)}")
    
    async def handle_typing(self, data):
        """Handle typing indicator"""
        try:
            is_typing = data.get('is_typing', False)
            
            if is_typing:
                await self.add_typing_status()
            else:
                await self.remove_typing_status()
            
            # Broadcast typing status to room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_indicator',
                    'user': self.user.username,
                    'user_id': self.user.id,
                    'is_typing': is_typing,
                }
            )
        except Exception as e:
            logger.error(f"Error handling typing: {e}")
    
    async def handle_call(self, data):
        """Handle call initiation with timeout logic"""
        try:
            call_type = data.get('call_type', 'audio')
            call_action = data.get('action', 'initiate')  # initiate, answer, decline, end
            call_id = data.get('call_id')
            
            if call_action == 'initiate':
                call = await self.initiate_call(call_type)
                
                # Start call timeout task (auto-decline after 30 seconds)
                self.call_timeout_task = asyncio.create_task(
                    self.handle_call_timeout(call.id)
                )
                
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'call_initiated',
                        'call_id': str(call.id),
                        'initiator': call.initiator.username,
                        'initiator_id': call.initiator.id,
                        'call_type': call.call_type,
                        'timestamp': timezone.now().isoformat(),
                    }
                )
                
                # Send ringing notification
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'call_ringing',
                        'call_id': str(call.id),
                        'caller_name': call.initiator.first_name or call.initiator.username,
                        'call_type': call.call_type,
                    }
                )
                
            elif call_action == 'answer':
                # Cancel timeout on answer
                if self.call_timeout_task:
                    self.call_timeout_task.cancel()
                    self.call_timeout_task = None
                
                await self.update_call_status(call_id, 'answered')
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'call_answered',
                        'call_id': call_id,
                    }
                )
            elif call_action == 'decline':
                # Cancel timeout on decline
                if self.call_timeout_task:
                    self.call_timeout_task.cancel()
                    self.call_timeout_task = None
                    
                await self.update_call_status(call_id, 'declined')
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'call_declined',
                        'call_id': call_id,
                    }
                )
            elif call_action == 'end':
                # Cancel timeout on end
                if self.call_timeout_task:
                    self.call_timeout_task.cancel()
                    self.call_timeout_task = None
                    
                await self.update_call_status(call_id, 'ended')
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'call_ended',
                        'call_id': call_id,
                    }
                )
        except Exception as e:
            logger.error(f"Error handling call: {e}")
            await self.send_error(f"Error with call: {str(e)}")
    
    async def handle_read_receipt(self, data):
        """Handle read receipt for a message"""
        try:
            message_id = data.get('message_id')
            
            # Mark message as read
            await self.mark_message_as_read(message_id)
            
            # Broadcast read receipt to room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message_read',
                    'message_id': message_id,
                    'read_by': self.user.username,
                    'read_by_id': self.user.id,
                    'read_at': timezone.now().isoformat(),
                }
            )
        except Exception as e:
            logger.error(f"Error handling read receipt: {e}")
    
    # ==================== WebRTC Signaling ====================
    
    async def handle_webrtc_offer(self, data):
        """Handle WebRTC SDP offer"""
        try:
            call_id = data.get('call_id')
            offer = data.get('offer')
            
            # Store offer in database
            await self.store_webrtc_offer(call_id, offer)
            
            # Relay offer to receiver
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'webrtc_offer',
                    'call_id': call_id,
                    'offer': offer,
                }
            )
        except Exception as e:
            logger.error(f"Error handling WebRTC offer: {e}")
            await self.send_error(f"Error with WebRTC offer: {str(e)}")
    
    async def handle_webrtc_answer(self, data):
        """Handle WebRTC SDP answer"""
        try:
            call_id = data.get('call_id')
            answer = data.get('answer')
            
            # Store answer in database
            await self.store_webrtc_answer(call_id, answer)
            
            # Relay answer to initiator
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'webrtc_answer',
                    'call_id': call_id,
                    'answer': answer,
                }
            )
        except Exception as e:
            logger.error(f"Error handling WebRTC answer: {e}")
            await self.send_error(f"Error with WebRTC answer: {str(e)}")
    
    async def handle_ice_candidate(self, data):
        """Handle ICE candidate"""
        try:
            call_id = data.get('call_id')
            candidate = data.get('candidate')
            
            # Store candidate in database
            await self.store_ice_candidate(call_id, candidate)
            
            # Relay candidate to other peer
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'ice_candidate',
                    'call_id': call_id,
                    'candidate': candidate,
                }
            )
        except Exception as e:
            logger.error(f"Error handling ICE candidate: {e}")
    
    async def handle_call_timeout(self, call_id):
        """Auto-decline call after timeout"""
        try:
            await asyncio.sleep(CALL_TIMEOUT_SECONDS)
            
            # Check if call is still in ringing state
            call = await self.get_call_by_id(call_id)
            
            if call and call.status == 'initiated':
                # Auto-decline the call
                await self.update_call_status(str(call_id), 'missed')
                
                # Notify both users
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'call_missed',
                        'call_id': str(call_id),
                        'reason': 'no_answer',
                    }
                )
                
                logger.info(f"Call {call_id} auto-declined due to timeout")
        except asyncio.CancelledError:
            # Task was cancelled (call answered/declined before timeout)
            pass
        except Exception as e:
            logger.error(f"Error in call timeout handler: {e}")
    
    # ==================== Database Operations ====================
    
    @database_sync_to_async
    def verify_conversation_access(self):
        """Verify that user is part of the conversation"""
        from django.db.models import Q
        return Conversation.objects.filter(
            id=self.room_name
        ).filter(
            Q(participant1=self.user) | Q(participant2=self.user)
        ).exists()
    
    @database_sync_to_async
    def save_message(self, content):
        """Save message to database"""
        conversation = Conversation.objects.get(id=self.room_name)
        message = Message.objects.create(
            conversation=conversation,
            sender=self.user,
            content=content,
            message_type='text',
        )
        # Update conversation's last message and updated_at
        conversation.last_message = message
        conversation.save(update_fields=['last_message', 'updated_at'])
        return message
    
    @database_sync_to_async
    def add_typing_status(self):
        """Add or update typing status"""
        conversation = Conversation.objects.get(id=self.room_name)
        Typing.objects.update_or_create(
            conversation=conversation,
            user=self.user,
        )
    
    @database_sync_to_async
    def remove_typing_status(self):
        """Remove typing status with proper error logging"""
        try:
            conversation = Conversation.objects.get(id=self.room_name)
            deleted_count, _ = Typing.objects.filter(
                conversation=conversation, 
                user=self.user
            ).delete()
            
            if deleted_count > 0:
                logger.debug(f"Typing status removed for {self.user.username} in conversation {self.room_name}")
        except Conversation.DoesNotExist:
            logger.warning(f"Conversation {self.room_name} not found when removing typing status")
        except Exception as e:
            logger.error(f"Error removing typing status: {e}", exc_info=True)
    
    @database_sync_to_async
    def mark_message_as_read(self, message_id):
        """Mark a message as read - with conversation validation"""
        try:
            # CRITICAL: Verify message belongs to this conversation
            message = Message.objects.get(
                id=message_id,
                conversation_id=self.room_name
            )
            
            # Only mark as read if the current user is not the sender
            if message.sender.id != self.user.id:
                message.mark_as_read()
                logger.info(f"Message {message_id} marked as read by {self.user.username}")
            else:
                logger.warning(f"User {self.user.username} tried to mark own message as read")
        except Message.DoesNotExist:
            logger.warning(f"Message {message_id} not found in conversation {self.room_name}")
    
    @database_sync_to_async
    def initiate_call(self, call_type):
        """Create a call record"""
        conversation = Conversation.objects.get(id=self.room_name)
        receiver = conversation.get_other_user(self.user)
        call = Call.objects.create(
            conversation=conversation,
            initiator=self.user,
            receiver=receiver,
            call_type=call_type,
            status='initiated',
        )
        return call
    
    @database_sync_to_async
    def update_call_status(self, call_id, status):
        """Update call status"""
        call = Call.objects.get(id=call_id)
        call.status = status
        
        if status == 'answered':
            call.started_at = timezone.now()
            call.is_answered = True
        elif status == 'missed':
            call.is_missed = True
            call.ended_at = timezone.now()
        elif status in ['declined', 'ended']:
            if not call.ended_at:
                call.ended_at = timezone.now()
                if call.started_at:
                    call.duration = int((call.ended_at - call.started_at).total_seconds())
        
        call.save()
        return call
    
    @database_sync_to_async
    def store_webrtc_offer(self, call_id, offer):
        """Store WebRTC SDP offer"""
        try:
            call = Call.objects.get(id=call_id)
            call.webrtc_offer = offer
            call.save(update_fields=['webrtc_offer'])
        except Call.DoesNotExist:
            logger.warning(f"Call {call_id} not found when storing offer")
    
    @database_sync_to_async
    def store_webrtc_answer(self, call_id, answer):
        """Store WebRTC SDP answer"""
        try:
            call = Call.objects.get(id=call_id)
            call.webrtc_answer = answer
            call.save(update_fields=['webrtc_answer'])
        except Call.DoesNotExist:
            logger.warning(f"Call {call_id} not found when storing answer")
    
    @database_sync_to_async
    def store_ice_candidate(self, call_id, candidate):
        """Store ICE candidate"""
        try:
            call = Call.objects.get(id=call_id)
            if not call.ice_candidates:
                call.ice_candidates = []
            call.ice_candidates.append(candidate)
            call.save(update_fields=['ice_candidates'])
        except Call.DoesNotExist:
            logger.warning(f"Call {call_id} not found when storing ICE candidate")
    
    @database_sync_to_async
    def get_call_by_id(self, call_id):
        """Get call by ID"""
        try:
            return Call.objects.get(id=call_id)
        except Call.DoesNotExist:
            return None
    
    # ==================== Message Handlers ====================
    
    async def chat_message(self, event):
        """Handle chat message event"""
        # Don't send message back to the sender
        if event['sender_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'message',
                'message_id': event['message_id'],
                'sender': event['sender'],
                'sender_id': event['sender_id'],
                'content': event['content'],
                'created_at': event['created_at'],
                'is_read': event['is_read'],
            }))
    
    async def typing_indicator(self, event):
        """Handle typing indicator event"""
        # Don't send typing indicator back to the sender
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'user': event['user'],
                'user_id': event['user_id'],
                'is_typing': event['is_typing'],
            }))
    
    async def user_status(self, event):
        """Handle user online/offline status event"""
        # Send status update to all users in the conversation (including self)
        await self.send(text_data=json.dumps({
            'type': 'user_status',
            'user_id': event['user_id'],
            'username': event['username'],
            'status': event['status'],
        }))
    
    async def call_initiated(self, event):
        """Handle call initiated event"""
        await self.send(text_data=json.dumps({
            'type': 'call_initiated',
            'call_id': event['call_id'],
            'initiator': event['initiator'],
            'initiator_id': event['initiator_id'],
            'call_type': event['call_type'],
        }))
    
    async def call_answered(self, event):
        """Handle call answered event"""
        await self.send(text_data=json.dumps({
            'type': 'call_answered',
            'call_id': event['call_id'],
        }))
    
    async def call_declined(self, event):
        """Handle call declined event"""
        await self.send(text_data=json.dumps({
            'type': 'call_declined',
            'call_id': event['call_id'],
        }))
    
    async def call_ended(self, event):
        """Handle call ended event"""
        await self.send(text_data=json.dumps({
            'type': 'call_ended',
            'call_id': event['call_id'],
        }))
    
    async def call_ringing(self, event):
        """Handle call ringing notification"""
        # Only send to receiver (not initiator)
        await self.send(text_data=json.dumps({
            'type': 'call_ringing',
            'call_id': event['call_id'],
            'caller_name': event['caller_name'],
            'call_type': event['call_type'],
        }))
    
    async def call_missed(self, event):
        """Handle missed call notification"""
        await self.send(text_data=json.dumps({
            'type': 'call_missed',
            'call_id': event['call_id'],
            'reason': event['reason'],
        }))
    
    async def webrtc_offer(self, event):
        """Handle WebRTC offer relay"""
        await self.send(text_data=json.dumps({
            'type': 'webrtc_offer',
            'call_id': event['call_id'],
            'offer': event['offer'],
        }))
    
    async def webrtc_answer(self, event):
        """Handle WebRTC answer relay"""
        await self.send(text_data=json.dumps({
            'type': 'webrtc_answer',
            'call_id': event['call_id'],
            'answer': event['answer'],
        }))
    
    async def ice_candidate(self, event):
        """Handle ICE candidate relay"""
        await self.send(text_data=json.dumps({
            'type': 'ice_candidate',
            'call_id': event['call_id'],
            'candidate': event['candidate'],
        }))
    
    async def message_read(self, event):
        """Handle message read receipt event"""
        # Send to all users in the room
        logger.info(f"Broadcasting read receipt for message {event['message_id']}")
        await self.send(text_data=json.dumps({
            'type': 'message_read',
            'message_id': event['message_id'],
            'read_by': event['read_by'],
            'read_by_id': event['read_by_id'],
            'read_at': event['read_at'],
        }))
    
    async def batch_messages_read(self, event):
        """Handle batch read receipt event"""
        # Send to all users in the room (especially senders of the messages)
        await self.send(text_data=json.dumps({
            'type': 'batch_messages_read',
            'message_ids': event['message_ids'],
            'read_by': event['read_by'],
            'read_by_id': event['read_by_id'],
            'read_at': event['read_at'],
            'count': len(event['message_ids']),
        }))
    
    async def send_error(self, message):
        """Send error message to client"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message,
        }))
