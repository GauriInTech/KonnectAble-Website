from django.urls import path
from . import views

app_name = 'message'

urlpatterns = [
    path('chat/<int:other_user_id>/', views.chat_with_user, name='chat_with_user'),
    path('inbox/', views.inbox, name='inbox'),
    path('api/conversation/<int:conversation_id>/messages/', views.conversation_messages, name='conversation_messages'),
    path('api/conversation/<int:conversation_id>/send/', views.send_message, name='conversation_send'),
]
