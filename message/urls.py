from django.urls import path
from . import views

app_name = 'message'

urlpatterns = [
    path('chat/<int:other_user_id>/', views.chat_with_user, name='chat_with_user'),
    path('chat/conversation/<int:conversation_id>/', views.chat_conversation, name='chat_conversation'),
    path('chat/create_group/', views.create_group, name='create_group'),
    path('chat/conversation/<int:conversation_id>/leave/', views.leave_conversation, name='leave_conversation'),
    path('inbox/', views.inbox, name='inbox'),
    path('api/conversation/<int:conversation_id>/messages/', views.conversation_messages, name='conversation_messages'),
    path('api/conversation/<int:conversation_id>/send/', views.send_message, name='conversation_send'),
    path('api/conversation/<int:conversation_id>/add_member/', views.add_member, name='add_member'),
    path('api/conversation/<int:conversation_id>/remove_member/', views.remove_member, name='remove_member'),
    path('api/conversation/<int:conversation_id>/update_name/', views.update_group_name, name='update_group_name'),
    path('api/conversation/<int:conversation_id>/promote_admin/', views.promote_admin, name='promote_admin'),
    path('api/conversation/<int:conversation_id>/demote_admin/', views.demote_admin, name='demote_admin'),
    path('api/conversation/<int:conversation_id>/delete/', views.delete_group, name='delete_group'),
    path('api/users/search/', views.search_users, name='search_users'),
]
