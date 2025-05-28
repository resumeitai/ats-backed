from django.contrib import admin
from .models import Resume, ResumeVersion, ResumeSection


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Resume model.
    """
    list_display = ('title', 'user', 'template', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at', 'updated_at')
    search_fields = ('title', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ResumeVersion)
class ResumeVersionAdmin(admin.ModelAdmin):
    """
    Admin configuration for the ResumeVersion model.
    """
    list_display = ('resume', 'version_number', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('resume__title', 'resume__user__username')
    readonly_fields = ('created_at',)


@admin.register(ResumeSection)
class ResumeSectionAdmin(admin.ModelAdmin):
    """
    Admin configuration for the ResumeSection model.
    """
    list_display = ('name', 'type', 'is_required', 'order')
    list_filter = ('type', 'is_required')
    search_fields = ('name',)