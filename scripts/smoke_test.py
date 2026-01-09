import os
import django
import sys
from pathlib import Path

# ensure project root is on PYTHONPATH so Django settings package can be imported
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'KonnectAble.settings')
django.setup()

from django.contrib.auth import get_user_model
from message.models import Conversation, Message
from django.utils import timezone

User = get_user_model()

u1, created = User.objects.get_or_create(username='auto_test_a')
if created:
    u1.set_password('pass')
    u1.save()

u2, created = User.objects.get_or_create(username='auto_test_b')
if created:
    u2.set_password('pass')
    u2.save()

conv = Conversation.objects.create()
conv.participants.add(u1, u2)

msg = Message.objects.create(conversation=conv, sender=u1, content='smoke hello', created_at=timezone.now())
print('created', msg.pk, msg.is_read)

msgs = Message.objects.filter(conversation=conv, pk__in=[msg.pk]).exclude(sender=u2).filter(is_read=False)
print('to_mark', list(msgs.values_list('id', flat=True)))

msgs.update(is_read=True)
print('after', Message.objects.get(pk=msg.pk).is_read)
