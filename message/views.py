from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from .models import Conversation, Message

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

    return render(request, 'message/chat.html', {
        'conversation_id': conversation.pk,
        'other_user': other,
    })


@login_required
def conversation_messages(request, conversation_id):
    conv = get_object_or_404(Conversation, pk=conversation_id)
    if not conv.participants.filter(pk=request.user.pk).exists():
        return HttpResponseForbidden()

    msgs = conv.messages.all().order_by('created_at')[:200]
    data = [
        {
            'id': m.pk,
            'sender_id': m.sender_id,
            'content': m.content,
            'created_at': m.created_at.isoformat(),
            'sender_username': getattr(m.sender, 'username', ''),
            'sender_full_name': getattr(m.sender, 'get_full_name', lambda: '')() if hasattr(m.sender, 'get_full_name') else '',
            'sender_avatar': (m.sender.profile.profile_image.url if getattr(getattr(m.sender, 'profile', None), 'profile_image', None) else ''),
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
    users = User.objects.exclude(pk=request.user.pk).order_by('username')[:100]

    return render(request, 'message/inbox.html', {'conversation_items': items, 'users': users})


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
    return JsonResponse({'message': data})
from django.shortcuts import render


@login_required
def chat_conversation(request, conversation_id):
    conv = get_object_or_404(Conversation, pk=conversation_id)
    if not conv.participants.filter(pk=request.user.pk).exists():
        return HttpResponseForbidden()

    others = conv.participants.exclude(pk=request.user.pk)
    other_user = others.first() if others.count() == 1 else None
    participants = conv.participants.all()

    return render(request, 'message/chat.html', {
        'conversation_id': conv.pk,
        'other_user': other_user,
        'participants': participants,
        'conversation': conv,
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
    conv = Conversation.objects.create()
    # add creator + provided users
    conv.participants.add(request.user, *list(users))

    return redirect('message:chat_conversation', conversation_id=conv.pk)

# Create your views here.


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
