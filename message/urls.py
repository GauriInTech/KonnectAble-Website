from django.urls import path
from . import views
from django.views.generic import RedirectView

app_name = 'message'

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='message:inbox', permanent=False)),
    path('chat/<int:other_user_id>/', views.chat_with_user, name='chat_with_user'),
    path('chat/group/<int:conversation_id>/', views.chat_group, name='chat_group'),
    path('inbox/', views.inbox, name='inbox'),
    path('api/conversation/<int:conversation_id>/messages/', views.conversation_messages, name='conversation_messages'),
    path('api/conversation/<int:conversation_id>/send/', views.send_message, name='conversation_send'),
    path('api/message/<int:message_id>/edit/', views.edit_message, name='edit_message'),
    path('api/message/<int:message_id>/delete/', views.delete_message, name='delete_message'),
    path('api/message/<int:message_id>/reaction/add/', views.add_reaction, name='add_reaction'),
    path('api/message/<int:message_id>/reaction/remove/', views.remove_reaction, name='remove_reaction'),
    path('api/message/<int:message_id>/pin/', views.pin_message, name='pin_message'),
    path('api/conversation/<int:conversation_id>/pinned/', views.get_pinned_messages, name='pinned_messages'),
    path('api/user/<int:user_id>/status/', views.user_status, name='user_status'),
    path('api/users/for-group/', views.get_users_for_group, name='get_users_for_group'),
    path('api/group/create/', views.create_group, name='create_group'),
    path('api/group/<int:conversation_id>/details/', views.group_details, name='group_details'),
    path('api/group/<int:conversation_id>/add-member/', views.add_group_member, name='add_group_member'),
    path('api/group/<int:conversation_id>/remove-member/', views.remove_group_member, name='remove_group_member'),
    path('api/group/<int:conversation_id>/update/', views.update_group, name='update_group'),
    path('api/search/', views.search_messages, name='search_messages'),
]
