from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseForbidden
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from .models import Conversation, Message
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import json
from django.db import transaction

User = get_user_model()


@login_required
def chat_with_user(request, other_user_id):
    other = get_object_or_404(User, pk=other_user_id)
    # find or create conversation for these two users
    conv, created = Conversation.get_or_create_for_users([other.pk], created_by=request.user)
    conversation = conv

    return render(request, 'message/chat.html', {
        'conversation_id': conversation.pk,
        'other_user': other,
    })


@login_required
def conversation_messages(request, conversation_id):
    conv = get_object_or_404(Conversation, pk=conversation_id)
    if not conv.participants.filter(pk=request.user.pk).exists():
        return HttpResponseForbidden()

    # ✅ STEP 3: mark SENT → DELIVERED (atomic, per-message)
    delivered_ids = []
    try:
        with transaction.atomic():
            delivered_ids = Message.bulk_mark_delivered_for_user(conv, request.user)
    except Exception:
        delivered_ids = []

    # ✅ STEP 4: mark DELIVERED → SEEN (atomic, per-message)
    seen_ids = []
    try:
        with transaction.atomic():
            seen_ids = Message.bulk_mark_seen_for_user(conv, request.user)
    except Exception:
        seen_ids = []

    # Broadcast delivered events
    channel_layer = get_channel_layer()
    for mid in delivered_ids:
        async_to_sync(channel_layer.group_send)(
            f'chat_{conversation_id}',
            {
                'type': 'chat.delivered',
                'message_id': mid,
                'user_id': request.user.pk,
                'sender_id': (Message.objects.filter(pk=mid).values_list('sender_id', flat=True).first()),
                'status': 'delivered',
            }
        )

    # Broadcast read events
    for mid in seen_ids:
        async_to_sync(channel_layer.group_send)(
            f'chat_{conversation_id}',
            {
                'type': 'chat.read',
                'message_id': mid,
                'user_id': request.user.pk,
                'sender_id': (Message.objects.filter(pk=mid).values_list('sender_id', flat=True).first()),
                'status': 'seen',
            }
        )

    since_id = request.GET.get('since_id')
    if since_id:
        msgs = conv.messages.filter(id__gt=since_id).order_by('created_at')[:200]
    else:
        msgs = conv.messages.all().order_by('created_at')[:200]

    data = [
        {
            'id': m.pk,
            'sender_id': m.sender_id,
            'content': m.content,
            'created_at': m.created_at.isoformat(),
            'sender_username': getattr(m.sender, 'username', ''),
            'sender_full_name': getattr(m.sender, 'get_full_name', lambda: '')() if hasattr(m.sender, 'get_full_name') else '',
            'sender_avatar': (
                m.sender.profile.profile_image.url
                if getattr(getattr(m.sender, 'profile', None), 'profile_image', None)
                else ''
            ),
            'status': m.status,  # 👈 important for blue ticks
            'delivered_to': list(m.delivered_to.values_list('pk', flat=True)),
            'seen_by': list(m.seen_by.values_list('pk', flat=True)),
        }
        for m in msgs
    ]
    return JsonResponse({'messages': data})


@login_required
def inbox(request):
    # List conversations the user participates in and compute the other participant for 1:1 convs
    convs = Conversation.objects.filter(participants=request.user).order_by('-updated_at')
    items = []
    for c in convs:
        others = c.participants.exclude(pk=request.user.pk)
        other_user = others.first() if others.count() == 1 else None
        items.append({'conversation': c, 'other': other_user})

    # provide a short list of other users to allow creating groups from the UI
    # we don't render all users server-side anymore; the client will request matches
    users = []

    # surface any error message passed via querystring (e.g. validation feedback)
    error = request.GET.get('error', '')
    return render(request, 'message/inbox.html', {'conversation_items': items, 'users': users, 'error': error})


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

    msg = Message.objects.create(conversation=conv, sender=request.user, content=text)
    data = {
        'id': msg.pk,
        'sender_id': msg.sender_id,
        'content': msg.content,
        'created_at': msg.created_at.isoformat(),
    }
    # broadcast to websocket group so other connected clients see the message live
    try:
        channel_layer = get_channel_layer()
        payload = {
            'type': 'chat.message',
            'message': msg.content,
            'sender_id': msg.sender_id,
            'sender_username': (request.user.get_full_name() if hasattr(request.user, 'get_full_name') else request.user.username) or getattr(request.user, 'username', ''),
            'sender_avatar': (getattr(getattr(request.user, 'profile', None), 'profile_image', None).url if getattr(getattr(request.user, 'profile', None), 'profile_image', None) else ''),
            'message_id': msg.pk,
            'created_at': msg.created_at.isoformat(),
            'conversation_id': str(conversation_id),
        }
        async_to_sync(channel_layer.group_send)(f'chat_{conversation_id}', payload)
    except Exception:
        pass

    return JsonResponse({'message': data})


@login_required
def chat_conversation(request, conversation_id):
    conv = get_object_or_404(Conversation, pk=conversation_id)
    if not conv.participants.filter(pk=request.user.pk).exists():
        return HttpResponseForbidden()

    others = conv.participants.exclude(pk=request.user.pk)
    other_user = others.first() if others.count() == 1 else None
    participants = conv.participants.all()
    participant_ids = json.dumps(list(participants.values_list('pk', flat=True)))

    is_admin = conv.created_by == request.user or conv.admins.filter(pk=request.user.pk).exists()
    return render(request, 'message/chat.html', {
        'conversation_id': conv.pk,
        'other_user': other_user,
        'participants': participants,
        'participant_ids': participant_ids,
        'conversation': conv,
        'is_admin': is_admin,
    })


@login_required
def create_group(request):
    # Accepts POST with `user_ids` (comma-separated or multiple form fields) and creates a Conversation
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    # collect user ids
    user_ids = request.POST.getlist('user_ids') or request.POST.get('user_ids', '')
    if isinstance(user_ids, str):
        user_ids = [s.strip() for s in user_ids.split(',') if s.strip()]

    users = User.objects.filter(pk__in=user_ids)
    if users.count() == 0:
        # require at least one selected user
        return redirect(reverse('message:inbox') + '?error=' + 'Please+select+at+least+one+user')

    # desired participant ids (include creator)
    desired_ids = set([int(request.user.pk)]) | set(int(u.pk) for u in users)

    # try to find an existing conversation with exactly the same participants
    candidates = Conversation.objects.filter(participants__pk__in=desired_ids).distinct()
    for c in candidates:
        part_ids = set(c.participants.values_list('pk', flat=True))
        if part_ids == desired_ids:
            return redirect('message:chat_conversation', conversation_id=c.pk)

    # no match -> create a new conversation
    conv = Conversation.objects.create(created_by=request.user)
    conv.participants.add(request.user, *list(users))
    # make the creator an admin by default
    conv.admins.add(request.user)

    return redirect('message:chat_conversation', conversation_id=conv.pk)


@login_required
def search_users(request):
    # AJAX endpoint: GET ?q=term -> JSON list of matching users
    q = (request.GET.get('q') or '').strip()
    if not q:
        return JsonResponse({'users': []})

    from django.db.models import Q
    qs = User.objects.exclude(pk=request.user.pk).filter(
        Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q)
    ).order_by('username')[:30]

    results = []
    for u in qs:
        full_name = ''
        try:
            full_name = u.get_full_name() if hasattr(u, 'get_full_name') else ''
        except Exception:
            full_name = ''
        results.append({'id': u.pk, 'username': u.username, 'full_name': full_name})

    return JsonResponse({'users': results})


@login_required
def leave_conversation(request, conversation_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    conv = get_object_or_404(Conversation, pk=conversation_id)
    if not conv.participants.filter(pk=request.user.pk).exists():
        return HttpResponseForbidden()

    conv.participants.remove(request.user)
    # if conversation empty, delete it
    if conv.participants.count() == 0:
        conv.delete()

    return redirect('message:inbox')


@login_required
def add_member(request, conversation_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    conv = get_object_or_404(Conversation, pk=conversation_id)
    if not (conv.created_by == request.user or conv.admins.filter(pk=request.user.pk).exists()):
        return HttpResponseForbidden()

    user_id = request.POST.get('user_id')
    if not user_id:
        return JsonResponse({'error': 'user_id required'}, status=400)

    user = get_object_or_404(User, pk=user_id)
    if conv.participants.filter(pk=user.pk).exists():
        return JsonResponse({'error': 'User already in conversation'}, status=400)

    conv.participants.add(user)
    return JsonResponse({'success': True})


@login_required
def remove_member(request, conversation_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    conv = get_object_or_404(Conversation, pk=conversation_id)
    if not (conv.created_by == request.user or conv.admins.filter(pk=request.user.pk).exists()):
        return HttpResponseForbidden()

    user_id = request.POST.get('user_id')
    if not user_id:
        return JsonResponse({'error': 'user_id required'}, status=400)

    user = get_object_or_404(User, pk=user_id)
    if user == request.user:
        return JsonResponse({'error': 'Cannot remove yourself'}, status=400)

    conv.participants.remove(user)
    return JsonResponse({'success': True})


@login_required
def update_group_name(request, conversation_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    conv = get_object_or_404(Conversation, pk=conversation_id)
    if not (conv.created_by == request.user or conv.admins.filter(pk=request.user.pk).exists()):
        return HttpResponseForbidden()

    name = request.POST.get('name', '').strip()
    if not name:
        return JsonResponse({'error': 'Name required'}, status=400)

    conv.name = name
    conv.save()
    return JsonResponse({'success': True})


@login_required
def promote_admin(request, conversation_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    conv = get_object_or_404(Conversation, pk=conversation_id)
    if conv.created_by != request.user:
        return HttpResponseForbidden()

    user_id = request.POST.get('user_id')
    if not user_id:
        return JsonResponse({'error': 'user_id required'}, status=400)

    user = get_object_or_404(User, pk=user_id)
    if not conv.participants.filter(pk=user.pk).exists():
        return JsonResponse({'error': 'User not in conversation'}, status=400)

    if conv.admins.filter(pk=user.pk).exists():
        return JsonResponse({'error': 'User already admin'}, status=400)

    conv.admins.add(user)
    return JsonResponse({'success': True})


@login_required
def demote_admin(request, conversation_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    conv = get_object_or_404(Conversation, pk=conversation_id)
    if conv.created_by != request.user:
        return HttpResponseForbidden()

    user_id = request.POST.get('user_id')
    if not user_id:
        return JsonResponse({'error': 'user_id required'}, status=400)

    user = get_object_or_404(User, pk=user_id)
    if user == request.user:
        return JsonResponse({'error': 'Cannot demote yourself'}, status=400)

    conv.admins.remove(user)
    return JsonResponse({'success': True})


@login_required
def delete_group(request, conversation_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    conv = get_object_or_404(Conversation, pk=conversation_id)
    if conv.created_by != request.user:
        return HttpResponseForbidden()

    conv.delete()
    return JsonResponse({'success': True})
