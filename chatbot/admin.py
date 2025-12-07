from django.contrib import admin
from .models import ChatMessage

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'is_user', 'timestamp')
    list_filter = ('is_user', 'timestamp')
    search_fields = ('username', 'message')
    ordering = ('-timestamp',)
