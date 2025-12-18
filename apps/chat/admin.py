from django.contrib import admin
from .models import ChatSession, ChatMessage


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ['role', 'content', 'metadata', 'created_at']
    can_delete = False
    max_num = 0

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'get_message_count', 'is_archived', 'created_at', 'updated_at']
    list_filter = ['is_archived', 'created_at', 'updated_at']
    search_fields = ['user__email', 'title']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    inlines = [ChatMessageInline]

    fieldsets = (
        ('Información básica', {
            'fields': ('user', 'title', 'is_archived')
        }),
        ('Metadatos', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['session', 'role', 'content_preview', 'route_used', 'tokens_used', 'created_at']
    list_filter = ['role', 'created_at']
    search_fields = ['session__title', 'session__user__email', 'content']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Relaciones', {
            'fields': ('session', 'role')
        }),
        ('Contenido', {
            'fields': ('content',)
        }),
        ('Metadatos', {
            'fields': ('metadata', 'created_at')
        }),
    )

    def content_preview(self, obj):
        """Muestra una vista previa del contenido"""
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Vista previa'
