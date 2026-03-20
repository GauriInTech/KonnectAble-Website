from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import Conversation, Message, MessageReaction, UserOnlineStatus

User = get_user_model()


@login_required
def chat_with_user(request, other_user_id):
    other = get_object_or_404(User, pk=other_user_id)

    # try to find an existing one-on-one conversation
    conv = Conversation.objects.filter(participants=other).filter(participants=request.user).distinct()
    # narrow to conversations with exactly 2 participants
    conv = [c for c in conv if c.participants.count() == 2]
    if conv:
        conversation = conv[0]
    else:
        conversation = Conversation.objects.create()
        conversation.participants.add(request.user, other)

    # Mark all messages in this conversation as read
    conversation.messages.filter(sender=other, is_read=False).update(is_read=True)

    return render(request, 'message/chat.html', {
        'conversation_id': conversation.pk,
        'conversation': conversation,
        'other_user': other if not conversation.is_group else None,
        'is_group': conversation.is_group,
    })


@login_required
def chat_group(request, conversation_id):
    """Chat view for groups"""
    conversation = get_object_or_404(Conversation, pk=conversation_id, is_group=True)
    if not conversation.participants.filter(pk=request.user.pk).exists():
        return HttpResponseForbidden()

    # Mark all messages in this conversation as read (from others)
    conversation.messages.filter(~Q(sender=request.user), is_read=False).update(is_read=True)

    return render(request, 'message/chat.html', {
        'conversation_id': conversation.pk,
        'conversation': conversation,
        'other_user': None,
        'is_group': True,
    })


@login_required
def conversation_messages(request, conversation_id):
    conv = get_object_or_404(Conversation, pk=conversation_id)
    if not conv.participants.filter(pk=request.user.pk).exists():
        return HttpResponseForbidden()

    msgs = conv.messages.filter(is_deleted=False).order_by('created_at')[:200]
    data = [
        {
            'id': m.pk,
            'sender_id': m.sender_id,
            'content': m.content,
            'created_at': m.created_at.isoformat(),
            'updated_at': m.updated_at.isoformat(),
            'is_read': m.is_read,
            'is_edited': m.is_edited,
            'is_pinned': m.is_pinned,
            'status': getattr(m, 'status', 'sent'),
            'sender_username': getattr(m.sender, 'username', ''),
            'sender_full_name': getattr(m.sender, 'get_full_name', lambda: '')() if hasattr(m.sender, 'get_full_name') else '',
            'sender_avatar': (m.sender.profile.profile_image.url if getattr(getattr(m.sender, 'profile', None), 'profile_image', None) else ''),
            'reactions': list(m.reactions.values('emoji').annotate(count=__import__('django.db.models', fromlist=['Count']).Count('id')).values_list('emoji', 'count')) if m.reactions.exists() else [],
        }
        for m in msgs
    ]
    return JsonResponse({'messages': data})


@login_required
def inbox(request):
    # List conversations the user participates in and compute the other participant for 1:1 convs
    query = request.GET.get('q', '').strip()
    
    convs = Conversation.objects.filter(participants=request.user).order_by('-updated_at')
    
    # Search conversations by participant name or last message
    if query:
        convs = convs.filter(
            Q(participants__username__icontains=query) |
            Q(participants__first_name__icontains=query) |
            Q(participants__last_name__icontains=query) |
            Q(messages__content__icontains=query) |
            Q(name__icontains=query)  # Search group names
        ).distinct()
    
    items = []
    for c in convs:
        if c.is_group:
            # Group conversation
            other_user = None
            group_name = c.name or f"Group ({c.participants.count()} members)"
            group_description = c.description or ""
            avatar_url = c.group_image.url if c.group_image else None
            is_online = False  # Groups don't have online status
            unread_count = c.messages.filter(~Q(sender=request.user), is_read=False).count()
        else:
            # 1-on-1 conversation
            others = c.participants.exclude(pk=request.user.pk)
            other_user = others.first() if others.count() == 1 else None
            group_name = None
            group_description = ""
            avatar_url = None
            if other_user:
                avatar_url = (other_user.profile.profile_image.url if getattr(getattr(other_user, 'profile', None), 'profile_image', None) else '')
                try:
                    online_status = UserOnlineStatus.objects.get(user=other_user)
                    is_online = online_status.is_online
                except UserOnlineStatus.DoesNotExist:
                    is_online = False
                unread_count = c.messages.filter(sender=other_user, is_read=False).count()
            else:
                is_online = False
                unread_count = 0
        
        last_msg = c.get_last_message()
        
        items.append({
            'conversation': c,
            'is_group': c.is_group,
            'group_name': group_name,
            'group_description': group_description,
            'other': other_user,
            'last_message': last_msg,
            'last_message_preview': c.get_last_message_preview(),
            'avatar_url': avatar_url,
            'is_online': is_online,
            'unread_count': unread_count,
        })

    return render(request, 'message/inbox.html', {
        'conversation_items': items,
        'search_query': query,
    })


@login_required
def search_messages(request):
    """Search messages within conversations"""
    query = request.GET.get('q', '').strip()
    
    if not query or len(query) < 2:
        return JsonResponse({'results': []})
    
    # Get messages from user's conversations
    conversation_ids = Conversation.objects.filter(participants=request.user).values_list('id', flat=True)
    messages = Message.objects.filter(
        conversation_id__in=conversation_ids,
        content__icontains=query,
        is_deleted=False
    ).order_by('-created_at')[:50]
    
    data = [
        {
            'id': m.pk,
            'conversation_id': m.conversation_id,
            'sender': m.sender.get_full_name() or m.sender.username,
            'content': m.content[:100],
            'created_at': m.created_at.isoformat(),
        }
        for m in messages
    ]
    return JsonResponse({'results': data})


@login_required
def send_message(request, conversation_id):
    # Fallback HTTP endpoint to send a message when WebSocket isn't available
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    conv = get_object_or_404(Conversation, pk=conversation_id)
    if not conv.participants.filter(pk=request.user.pk).exists():
        return HttpResponseForbidden()

    text = request.POST.get('message') or request.body.decode('utf-8')
    if not text:
        return JsonResponse({'error': 'empty message'}, status=400)

    msg = Message.objects.create(conversation=conv, sender=request.user, content=text, status=Message.STATUS_SENT)
    data = {
        'id': msg.pk,
        'sender_id': msg.sender_id,
        'content': msg.content,
        'created_at': msg.created_at.isoformat(),
        'status': getattr(msg, 'status', 'sent'),
    }
    return JsonResponse({'message': data})


@login_required
def edit_message(request, message_id):
    """Edit a message"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    msg = get_object_or_404(Message, pk=message_id)
    
    # Only sender can edit
    if msg.sender_id != request.user.pk:
        return HttpResponseForbidden()
    
    # Cannot edit deleted messages
    if msg.is_deleted:
        return JsonResponse({'error': 'Cannot edit deleted message'}, status=400)

    new_content = request.POST.get('content', '').strip()
    if not new_content:
        return JsonResponse({'error': 'empty message'}, status=400)

    msg.content = new_content
    msg.is_edited = True
    msg.save()

    return JsonResponse({
        'id': msg.pk,
        'content': msg.content,
        'is_edited': msg.is_edited,
        'updated_at': msg.updated_at.isoformat(),
    })


@login_required
def delete_message(request, message_id):
    """Delete a message"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    msg = get_object_or_404(Message, pk=message_id)
    
    # Only sender can delete
    if msg.sender_id != request.user.pk:
        return HttpResponseForbidden()

    msg.is_deleted = True
    msg.content = "[Message deleted]"
    msg.save()

    return JsonResponse({'id': msg.pk, 'is_deleted': True})


@login_required
def add_reaction(request, message_id):
    """Add an emoji reaction to a message"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    msg = get_object_or_404(Message, pk=message_id)
    emoji = request.POST.get('emoji', '').strip()
    
    if not emoji:
        return JsonResponse({'error': 'emoji required'}, status=400)

    reaction, created = MessageReaction.objects.get_or_create(
        message=msg,
        user=request.user,
        emoji=emoji
    )

    return JsonResponse({
        'message_id': msg.pk,
        'emoji': emoji,
        'created': created,
    })


@login_required
def remove_reaction(request, message_id):
    """Remove an emoji reaction from a message"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    msg = get_object_or_404(Message, pk=message_id)
    emoji = request.POST.get('emoji', '').strip()
    
    if not emoji:
        return JsonResponse({'error': 'emoji required'}, status=400)

    MessageReaction.objects.filter(
        message=msg,
        user=request.user,
        emoji=emoji
    ).delete()

    return JsonResponse({
        'message_id': msg.pk,
        'emoji': emoji,
        'removed': True,
    })


@login_required
def pin_message(request, message_id):
    """Pin/unpin a message"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    msg = get_object_or_404(Message, pk=message_id)
    conv = msg.conversation

    # User must be participant
    if not conv.participants.filter(pk=request.user.pk).exists():
        return HttpResponseForbidden()

    msg.is_pinned = not msg.is_pinned
    msg.save()

    return JsonResponse({
        'message_id': msg.pk,
        'is_pinned': msg.is_pinned,
    })


@login_required
def get_pinned_messages(request, conversation_id):
    """Get all pinned messages in a conversation"""
    conv = get_object_or_404(Conversation, pk=conversation_id)
    
    if not conv.participants.filter(pk=request.user.pk).exists():
        return HttpResponseForbidden()

    pinned = conv.messages.filter(is_pinned=True, is_deleted=False).order_by('-created_at')
    
    data = [
        {
            'id': m.pk,
            'sender': m.sender.get_full_name() or m.sender.username,
            'content': m.content,
            'created_at': m.created_at.isoformat(),
        }
        for m in pinned
    ]
    return JsonResponse({'pinned_messages': data})


@login_required
def create_group(request):
    """Create a new group conversation"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()
    member_ids = request.POST.getlist('members[]')

    if not name:
        return JsonResponse({'error': 'Group name is required'}, status=400)

    if len(member_ids) < 1:  # At least one other member besides creator
        return JsonResponse({'error': 'At least one member required'}, status=400)

    # Create group
    group = Conversation.objects.create(
        is_group=True,
        name=name,
        description=description,
        admin=request.user
    )

    # Add creator and members
    group.participants.add(request.user)
    for member_id in member_ids:
        try:
            user = User.objects.get(pk=member_id)
            group.participants.add(user)
        except User.DoesNotExist:
            pass

    return JsonResponse({
        'id': group.pk,
        'name': group.name,
        'description': group.description,
        'member_count': group.participants.count(),
    })


@login_required
def group_details(request, conversation_id):
    """Get group details including members"""
    conv = get_object_or_404(Conversation, pk=conversation_id)
    if not conv.is_group:
        return JsonResponse({'error': 'Not a group'}, status=400)
    
    if not conv.participants.filter(pk=request.user.pk).exists():
        return HttpResponseForbidden()

    members = []
    for user in conv.participants.all():
        members.append({
            'id': user.pk,
            'username': user.username,
            'full_name': user.get_full_name() or user.username,
            'is_admin': conv.admin_id == user.pk,
            'avatar': (user.profile.profile_image.url if getattr(getattr(user, 'profile', None), 'profile_image', None) else ''),
        })

    return JsonResponse({
        'id': conv.pk,
        'name': conv.name,
        'description': conv.description,
        'admin_id': conv.admin_id,
        'member_count': len(members),
        'members': members,
        'group_image': conv.group_image.url if conv.group_image else None,
    })


@login_required
def add_group_member(request, conversation_id):
    """Add a member to a group (admin only)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    conv = get_object_or_404(Conversation, pk=conversation_id)
    if not conv.is_group or conv.admin_id != request.user.pk:
        return HttpResponseForbidden()

    user_id = request.POST.get('user_id')
    try:
        user = User.objects.get(pk=user_id)
        conv.participants.add(user)
        return JsonResponse({'success': True, 'user_id': user.pk})
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)


@login_required
def remove_group_member(request, conversation_id):
    """Remove a member from a group (admin only)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    conv = get_object_or_404(Conversation, pk=conversation_id)
    if not conv.is_group or conv.admin_id != request.user.pk:
        return HttpResponseForbidden()

    user_id = request.POST.get('user_id')
    if int(user_id) == request.user.pk:
        return JsonResponse({'error': 'Cannot remove yourself'}, status=400)

    try:
        user = User.objects.get(pk=user_id)
        conv.participants.remove(user)
        return JsonResponse({'success': True, 'user_id': user.pk})
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)


@login_required
def update_group(request, conversation_id):
    """Update group name/description (admin only)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    conv = get_object_or_404(Conversation, pk=conversation_id)
    if not conv.is_group or conv.admin_id != request.user.pk:
        return HttpResponseForbidden()

    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()

    if name:
        conv.name = name
    conv.description = description
    conv.save()

    return JsonResponse({
        'id': conv.pk,
        'name': conv.name,
        'description': conv.description,
    })


@login_required
def get_users_for_group(request):
    """Get users that can be added to groups (excluding current user)"""
    query = request.GET.get('q', '').strip()
    
    users = User.objects.exclude(pk=request.user.pk)
    
    if query:
        users = users.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        )
    
    users = users[:20]  # Limit results
    
    data = []
    for user in users:
        data.append({
            'id': user.pk,
            'username': user.username,
            'full_name': user.get_full_name() or user.username,
            'email': user.email,
            'avatar': (user.profile.profile_image.url if getattr(getattr(user, 'profile', None), 'profile_image', None) else ''),
        })
    
    return JsonResponse({'users': data})


@login_required
def user_status(request, user_id):
    """Return a user's online status for the chat UI."""
    target = get_object_or_404(User, pk=user_id)
    status, _ = UserOnlineStatus.objects.get_or_create(user=target)

    return JsonResponse({
        'user_id': target.pk,
        'username': target.username,
        'is_online': status.is_online,
        'last_seen': status.last_seen.isoformat() if status.last_seen else None,
    })
