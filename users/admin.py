from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, UserActivity, Referral


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Admin configuration for the custom User model.
    """
    list_display = ('username', 'email', 'full_name', 'role', 'is_verified', 'is_staff')
    list_filter = ('role', 'is_verified', 'is_staff', 'is_superuser', 'created_at')
    search_fields = ('username', 'email', 'full_name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('full_name', 'email', 'phone_number')}),
        (_('Permissions'), {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'is_verified', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'full_name', 'password1', 'password2'),
        }),
    )


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    """
    Admin configuration for the UserActivity model.
    """
    list_display = ('user', 'activity_type', 'created_at')
    list_filter = ('activity_type', 'created_at')
    search_fields = ('user__username', 'user__email', 'activity_type', 'description')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Referral model.
    """
    list_display = ('referrer', 'referred', 'code', 'is_successful', 'created_at')
    list_filter = ('is_successful', 'created_at')
    search_fields = ('referrer__username', 'referred__username', 'code')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)