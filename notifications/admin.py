from django.contrib import admin
from .models import Notification, EmailTemplate


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Notification model.
    """
    list_display = ('user', 'type', 'title', 'is_read', 'created_at')
    list_filter = ('type', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'user__username', 'user__email')
    readonly_fields = ('created_at',)
    list_per_page = 25


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    """
    Admin configuration for the EmailTemplate model.
    """
    list_display = ('name', 'subject', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'subject')
