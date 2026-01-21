from django.contrib import admin
from .models import Conversation, Message, Call, Typing


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'participant1', 'participant2', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('participant1__username', 'participant2__username')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'conversation', 'message_type', 'is_read', 'created_at')
    list_filter = ('message_type', 'is_read', 'created_at')
    search_fields = ('sender__username', 'content')
    readonly_fields = ('id', 'created_at', 'read_at')


@admin.register(Call)
class CallAdmin(admin.ModelAdmin):
    list_display = ('id', 'initiator', 'receiver', 'call_type', 'status', 'duration', 'initiated_at')
    list_filter = ('call_type', 'status', 'initiated_at')
    search_fields = ('initiator__username', 'receiver__username')
    readonly_fields = ('id', 'initiated_at', 'started_at', 'ended_at')


@admin.register(Typing)
class TypingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'conversation', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username',)
    readonly_fields = ('id', 'created_at')
