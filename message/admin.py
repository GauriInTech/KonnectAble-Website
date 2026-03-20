from django.contrib import admin
from .models import Conversation, Message, MessageReaction, UserOnlineStatus


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'updated_at', 'get_participants')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('participants__username',)
    
    def get_participants(self, obj):
        return ', '.join([p.username for p in obj.participants.all()])
    get_participants.short_description = 'Participants'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'conversation', 'created_at', 'status', 'is_read', 'is_edited', 'is_deleted', 'is_pinned')
    list_filter = ('created_at', 'status', 'is_read', 'is_edited', 'is_deleted', 'is_pinned')
    search_fields = ('content', 'sender__username', 'conversation__id')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(MessageReaction)
class MessageReactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'message', 'user', 'emoji', 'created_at')
    list_filter = ('emoji', 'created_at')
    search_fields = ('user__username', 'message__id')
    readonly_fields = ('created_at',)


@admin.register(UserOnlineStatus)
class UserOnlineStatusAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_online', 'last_seen')
    list_filter = ('is_online', 'last_seen')
    search_fields = ('user__username',)
    readonly_fields = ('last_seen',)
