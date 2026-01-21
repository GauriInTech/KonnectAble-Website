from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.views.generic import View
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.db.models import Q, Prefetch
from django.core.paginator import Paginator
import json
import logging

from accounts.models import User
from .models import Conversation, Message, Call
from .forms import MessageForm, CallForm

logger = logging.getLogger(__name__)


@login_required
def inbox_view(request):
    """
    Display the user's inbox with all conversations.
    Shows the latest message from each conversation and unread counts.
    """
    user = request.user
    
    # Get all conversations for the current user
    conversations = Conversation.objects.filter(
        Q(participant1=user) | Q(participant2=user)
    ).prefetch_related(
        'messages',
        'participant1',
        'participant2'
    ).order_by('-updated_at')
    
    # Count unread messages per conversation
    conversation_data = []
    for conv in conversations:
        unread_count = conv.messages.filter(
            ~Q(sender=user),
            is_read=False
        ).count()
        conversation_data.append({
            'conversation': conv,
            'unread_count': unread_count,
            'other_user': conv.get_other_user(user),
        })
    
    context = {
        'conversations': conversation_data,
        'total_unread': sum(c['unread_count'] for c in conversation_data),
    }
    
    return render(request, 'message/inbox.html', context)


@login_required
def conversation_detail_view(request, conversation_id):
    """
    Display detailed conversation with all messages between two users.
    Handles message sending and read receipts.
    """
    user = request.user
    try:
        conversation = Conversation.objects.get(
            Q(participant1=user, id=conversation_id) | Q(participant2=user, id=conversation_id)
        )
    except Conversation.DoesNotExist:
        raise Http404("Conversation not found")
    
    # Get other user
    other_user = conversation.get_other_user(user)
    
    # Mark all unread messages from other user as read
    unread_messages = Message.objects.filter(
        conversation=conversation,
        sender=other_user,
        is_read=False
    ).select_related('sender')
    
    # Get list of message IDs before updating
    unread_message_ids = list(unread_messages.values_list('id', flat=True))
    
    # Update database
    unread_messages.update(is_read=True, read_at=timezone.now())
    
    # Broadcast read receipts via WebSocket to notify sender
    if unread_message_ids:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        room_group_name = f'chat_{conversation_id}'
        
        # Send a batch read notification
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'batch_messages_read',
                'message_ids': [str(msg_id) for msg_id in unread_message_ids],
                'read_by': user.username,
                'read_by_id': user.id,
                'read_at': timezone.now().isoformat(),
            }
        )
        logger.info(f"Marked {len(unread_message_ids)} messages as read for {user.username}")
    
    # Get paginated messages
    messages = conversation.messages.all().order_by('created_at')
    paginator = Paginator(messages, 50)  # 50 messages per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get recent calls
    recent_calls = Call.objects.filter(
        conversation=conversation
    ).order_by('-initiated_at')[:10]
    
    form = MessageForm()
    call_form = CallForm()
    
    context = {
        'conversation': conversation,
        'other_user': other_user,
        'page_obj': page_obj,
        'messages': page_obj.object_list,
        'form': form,
        'call_form': call_form,
        'recent_calls': recent_calls,
    }
    
    return render(request, 'message/conversation_detail.html', context)


@login_required
def start_conversation_view(request, user_id):
    """
    Start or get existing conversation with a specific user by ID.
    """
    user = request.user
    other_user = get_object_or_404(User, id=user_id)
    
    if user == other_user:
        return redirect('message:inbox')
    
    # Get or create conversation
    conversation, created = Conversation.objects.get_or_create(
        participant1=min(user, other_user, key=lambda u: u.id),
        participant2=max(user, other_user, key=lambda u: u.id),
    )
    
    return redirect('message:conversation_detail', conversation_id=conversation.id)


# ==================== API Views ====================

@method_decorator(login_required, name='dispatch')
class ConversationListAPIView(View):
    """API endpoint to get list of conversations with metadata"""
    
    def get(self, request):
        user = request.user
        conversations = Conversation.objects.filter(
            Q(participant1=user) | Q(participant2=user)
        ).values('id', 'participant1__username', 'participant2__username', 'updated_at').order_by('-updated_at')
        
        conv_list = []
        for conv in conversations:
            other_username = (
                conv['participant2__username'] 
                if conv['participant1__username'] == user.username 
                else conv['participant1__username']
            )
            conv_list.append({
                'id': str(conv['id']),
                'other_user': other_username,
                'updated_at': conv['updated_at'].isoformat(),
            })
        
        return JsonResponse({'conversations': conv_list})


@method_decorator(login_required, name='dispatch')
class MessageListAPIView(View):
    """API endpoint to get messages from a conversation with pagination"""
    
    def get(self, request, conversation_id):
        user = request.user
        conversation = get_object_or_404(
            Conversation,
            Q(participant1=user) | Q(participant2=user),
            id=conversation_id
        )
        
        # Get pagination parameters
        page = int(request.GET.get('page', 1))
        limit = int(request.GET.get('limit', 50))
        offset = (page - 1) * limit
        
        # Get messages
        messages = Message.objects.filter(
            conversation=conversation
        ).order_by('-created_at')[offset:offset + limit]
        
        messages_data = []
        for msg in reversed(messages):  # Reverse to show in chronological order
            messages_data.append({
                'id': str(msg.id),
                'sender': msg.sender.username,
                'sender_id': msg.sender.id,
                'content': msg.content,
                'message_type': msg.message_type,
                'image': msg.image.url if msg.image else None,
                'file': msg.file.url if msg.file else None,
                'created_at': msg.created_at.isoformat(),
                'is_read': msg.is_read,
                'read_at': msg.read_at.isoformat() if msg.read_at else None,
            })
        
        return JsonResponse({
            'messages': messages_data,
            'page': page,
            'limit': limit,
        })


@method_decorator(login_required, name='dispatch')
class SendMessageAPIView(View):
    """API endpoint to send a new message"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            conversation_id = data.get('conversation_id')
            content = data.get('content', '').strip()
            
            user = request.user
            conversation = get_object_or_404(
                Conversation,
                Q(participant1=user) | Q(participant2=user),
                id=conversation_id
            )
            
            if not content:
                return JsonResponse({'error': 'Message content cannot be empty'}, status=400)
            
            # Create message
            message = Message.objects.create(
                conversation=conversation,
                sender=user,
                content=content,
                message_type='text',
            )
            
            # Update conversation's last message
            conversation.last_message = message
            conversation.save(update_fields=['last_message', 'updated_at'])
            
            return JsonResponse({
                'success': True,
                'message': {
                    'id': str(message.id),
                    'sender': message.sender.username,
                    'content': message.content,
                    'created_at': message.created_at.isoformat(),
                    'is_read': message.is_read,
                }
            })
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(login_required, name='dispatch')
class MarkAsReadAPIView(View):
    """API endpoint to mark a message as read"""
    
    def post(self, request, message_id):
        user = request.user
        message = get_object_or_404(Message, id=message_id)
        
        # CRITICAL: Verify user is part of the conversation
        conversation = message.conversation
        if not (conversation.participant1 == user or conversation.participant2 == user):
            return JsonResponse({'error': 'Unauthorized'}, status=403)
        
        # Check if user is not the sender
        if message.sender == user:
            return JsonResponse({'error': 'Cannot mark your own message as read'}, status=400)
        
        message.mark_as_read()
        
        return JsonResponse({
            'success': True,
            'is_read': message.is_read,
            'read_at': message.read_at.isoformat(),
        })


@method_decorator(login_required, name='dispatch')
class InitiateCallAPIView(View):
    """API endpoint to initiate a call"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            conversation_id = data.get('conversation_id')
            call_type = data.get('call_type', 'audio')  # 'audio' or 'video'
            
            user = request.user
            conversation = get_object_or_404(
                Conversation,
                Q(participant1=user) | Q(participant2=user),
                id=conversation_id
            )
            
            receiver = conversation.get_other_user(user)
            
            # Create call
            call = Call.objects.create(
                conversation=conversation,
                initiator=user,
                receiver=receiver,
                call_type=call_type,
                status='initiated',
            )
            
            return JsonResponse({
                'success': True,
                'call': {
                    'id': str(call.id),
                    'initiator': call.initiator.username,
                    'receiver': call.receiver.username,
                    'call_type': call.call_type,
                    'status': call.status,
                    'initiated_at': call.initiated_at.isoformat(),
                }
            })
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(login_required, name='dispatch')
class UpdateCallAPIView(View):
    """API endpoint to update call status"""
    
    def post(self, request, call_id):
        try:
            data = json.loads(request.body)
            status = data.get('status')  # 'ringing', 'answered', 'declined'
            
            call = get_object_or_404(Call, id=call_id)
            user = request.user
            
            # Check permissions
            if user not in [call.initiator, call.receiver]:
                return JsonResponse({'error': 'Unauthorized'}, status=403)
            
            if status == 'answered':
                call.status = 'answered'
                call.started_at = timezone.now()
            elif status == 'declined':
                call.status = 'declined'
                call.ended_at = timezone.now()
            elif status == 'missed':
                call.status = 'missed'
                call.ended_at = timezone.now()
            elif status == 'ended':
                call.status = 'ended'
                if not call.ended_at:
                    call.ended_at = timezone.now()
                    if call.started_at:
                        call.duration = int((call.ended_at - call.started_at).total_seconds())
            
            call.save()
            
            return JsonResponse({
                'success': True,
                'call': {
                    'id': str(call.id),
                    'status': call.status,
                    'duration': call.duration,
                }
            })
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(login_required, name='dispatch')
class EndCallAPIView(View):
    """API endpoint to end a call"""
    
    def post(self, request, call_id):
        try:
            call = get_object_or_404(Call, id=call_id)
            user = request.user
            
            # Check permissions
            if user not in [call.initiator, call.receiver]:
                return JsonResponse({'error': 'Unauthorized'}, status=403)
            
            call.status = 'ended'
            call.ended_at = timezone.now()
            
            if call.started_at:
                call.duration = int((call.ended_at - call.started_at).total_seconds())
            
            call.save()
            
            return JsonResponse({
                'success': True,
                'call': {
                    'id': str(call.id),
                    'status': call.status,
                    'duration': call.duration,
                    'ended_at': call.ended_at.isoformat(),
                }
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@method_decorator(login_required, name='dispatch')
class AnswerCallAPIView(View):
    """API endpoint to answer a call"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            call_id = data.get('call_id')
            
            call = get_object_or_404(Call, id=call_id)
            user = request.user
            
            if user != call.receiver:
                return JsonResponse({'error': 'Only receiver can answer the call'}, status=403)
            
            call.status = 'answered'
            call.started_at = timezone.now()
            call.save()
            
            return JsonResponse({
                'success': True,
                'call': {
                    'id': str(call.id),
                    'status': call.status,
                    'started_at': call.started_at.isoformat(),
                }
            })
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(login_required, name='dispatch')
class DeclineCallAPIView(View):
    """API endpoint to decline a call"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            call_id = data.get('call_id')
            
            call = get_object_or_404(Call, id=call_id)
            user = request.user
            
            if user != call.receiver:
                return JsonResponse({'error': 'Only receiver can decline the call'}, status=403)
            
            call.status = 'declined'
            call.ended_at = timezone.now()
            call.save()
            
            return JsonResponse({
                'success': True,
                'call': {
                    'id': str(call.id),
                    'status': call.status,
                }
            })
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@method_decorator(login_required, name='dispatch')
class GetConversationMetadataAPIView(View):
    """API endpoint to get conversation metadata with unread counts"""
    
    def get(self, request, conversation_id):
        user = request.user
        conversation = get_object_or_404(
            Conversation,
            Q(participant1=user) | Q(participant2=user),
            id=conversation_id
        )
        
        other_user = conversation.get_other_user(user)
        unread_count = Message.objects.filter(
            conversation=conversation,
            sender=other_user,
            is_read=False
        ).count()
        
        return JsonResponse({
            'conversation_id': str(conversation.id),
            'other_user': {
                'id': other_user.id,
                'username': other_user.username,
                'first_name': other_user.first_name,
                'last_name': other_user.last_name,
            },
            'unread_count': unread_count,
            'created_at': conversation.created_at.isoformat(),
            'updated_at': conversation.updated_at.isoformat(),
        })


@login_required
def user_status_view(request, user_id):
    """
    API endpoint to check if a user is online or offline.
    Returns the current online status of the user.
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    
    # Check if user has active WebSocket connection
    # For now, we return 'offline' as default
    # In a production system, you'd track active connections
    status = 'offline'
    
    # You can implement more sophisticated tracking here
    # For example, track last_activity timestamp on User model
    # and consider them online if last_activity is recent
    
    return JsonResponse({
        'user_id': user_id,
        'username': user.username,
        'status': status,
    })