from django.urls import path
from . import views
from . import consumers

app_name = 'message'

urlpatterns = [
    # Conversation URLs
    path('inbox/', views.inbox_view, name='inbox'),
    path('conversation/<uuid:conversation_id>/', views.conversation_detail_view, name='conversation_detail'),
    path('start/<int:user_id>/', views.start_conversation_view, name='start_conversation'),
    
    # AJAX API endpoints
    path('api/conversations/', views.ConversationListAPIView.as_view(), name='api_conversations'),
    path('api/conversation/<uuid:conversation_id>/messages/', views.MessageListAPIView.as_view(), name='api_messages'),
    path('api/send-message/', views.SendMessageAPIView.as_view(), name='api_send_message'),
    path('api/mark-as-read/<uuid:message_id>/', views.MarkAsReadAPIView.as_view(), name='api_mark_as_read'),
    path('api/initiate-call/', views.InitiateCallAPIView.as_view(), name='api_initiate_call'),
    path('api/answer-call/', views.AnswerCallAPIView.as_view(), name='api_answer_call'),
    path('api/decline-call/', views.DeclineCallAPIView.as_view(), name='api_decline_call'),
    path('api/end-call/', views.EndCallAPIView.as_view(), name='api_end_call'),
    path('api/conversation/<uuid:conversation_id>/metadata/', views.GetConversationMetadataAPIView.as_view(), name='api_conversation_metadata'),
    
    # User status endpoint
    path('api/user/<int:user_id>/status/', views.user_status_view, name='api_user_status'),
]
