from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import User, UserActivity, Referral


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Admin configuration for the custom User model.
    """
    list_display = ('username', 'email', 'full_name', 'role', 'is_verified', 'subscription_status_display', 'is_staff')
    list_filter = ('role', 'is_verified', 'is_staff', 'is_superuser', 'created_at')
    search_fields = ('username', 'email', 'full_name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at', 'subscription_info_display')
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('full_name', 'email', 'phone_number')}),
        (_('Permissions'), {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'is_verified', 'groups', 'user_permissions'),
        }),
        (_('Subscription Info'), {'fields': ('subscription_info_display',)}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'full_name', 'password1', 'password2'),
        }),
    )
    
    def subscription_status_display(self, obj):
        """
        Display subscription status in the list view.
        """
        if hasattr(obj, 'is_subscribed') and obj.is_subscribed:
            current_sub = obj.current_subscription
            if current_sub:
                return format_html(
                    '<span style="color: green; font-weight: bold;">✓ {}</span>',
                    current_sub.plan.name
                )
        return format_html('<span style="color: red;">✗ No Active Subscription</span>')
    
    subscription_status_display.short_description = 'Subscription Status'
    
    def subscription_info_display(self, obj):
        """
        Display detailed subscription information in the detail view.
        """
        if hasattr(obj, 'get_subscription_status'):
            status_info = obj.get_subscription_status()
            
            if status_info['is_subscribed']:
                return format_html(
                    """
                    <div style="background: #e8f5e8; padding: 10px; border-radius: 5px;">
                        <strong>Active Subscription:</strong><br>
                        <strong>Plan:</strong> {}<br>
                        <strong>Status:</strong> <span style="color: green;">{}</span><br>
                        <strong>Start Date:</strong> {}<br>
                        <strong>End Date:</strong> {}<br>
                        <strong>Days Remaining:</strong> {}<br>
                        <strong>Auto Renew:</strong> {}<br>
                        <a href="{}" target="_blank">View Subscription Details</a>
                    </div>
                    """,
                    status_info['plan_name'],
                    status_info['status'].title(),
                    status_info['start_date'],
                    status_info['end_date'],
                    status_info['days_remaining'],
                    'Yes' if status_info['is_auto_renew'] else 'No',
                    reverse('admin:subscriptions_subscription_change', args=[status_info['subscription_id']])
                )
            else:
                return format_html(
                    '<div style="background: #ffeaea; padding: 10px; border-radius: 5px; color: #d63031;">'
                    '<strong>No Active Subscription</strong>'
                    '</div>'
                )
        
        # Fallback for users without subscription methods
        subscriptions = obj.subscriptions.filter(status='active').first()
        if subscriptions:
            return format_html('<span style="color: green;">Active Subscription Found</span>')
        return format_html('<span style="color: red;">No Active Subscription</span>')
    
    subscription_info_display.short_description = 'Subscription Details'
    
    def get_queryset(self, request):
        """
        Optimize queryset to reduce database queries.
        """
        queryset = super().get_queryset(request)
        return queryset.select_related().prefetch_related('subscriptions', 'subscriptions__plan')


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    """
    Admin configuration for the UserActivity model.
    """
    list_display = ('user', 'activity_type', 'description_short', 'created_at')
    list_filter = ('activity_type', 'created_at')
    search_fields = ('user__username', 'user__email', 'activity_type', 'description')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    list_per_page = 50
    
    def description_short(self, obj):
        """
        Display truncated description in list view.
        """
        if obj.description:
            return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
        return '-'
    
    description_short.short_description = 'Description'
    
    def get_queryset(self, request):
        """
        Optimize queryset to reduce database queries.
        """
        queryset = super().get_queryset(request)
        return queryset.select_related('user')


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Referral model.
    """
    list_display = ('referrer', 'referred', 'code', 'is_successful', 'referral_bonus_status', 'created_at')
    list_filter = ('is_successful', 'created_at')
    search_fields = ('referrer__username', 'referred__username', 'code')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    
    def referral_bonus_status(self, obj):
        """
        Display referral bonus status.
        """
        try:
            # Check if there's a related ReferralBonus
            from subscriptions.models import ReferralBonus
            bonus = ReferralBonus.objects.filter(referral=obj).first()
            
            if bonus:
                if bonus.is_applied:
                    return format_html('<span style="color: green;">✓ Bonus Applied</span>')
                else:
                    return format_html('<span style="color: orange;">⏳ Bonus Pending</span>')
            else:
                return format_html('<span style="color: gray;">No Bonus</span>')
        except:
            return '-'
    
    referral_bonus_status.short_description = 'Bonus Status'
    
    def get_queryset(self, request):
        """
        Optimize queryset to reduce database queries.
        """
        queryset = super().get_queryset(request)
        return queryset.select_related('referrer', 'referred')


# Optional: Add inline admin for subscriptions in User admin
class SubscriptionInline(admin.TabularInline):
    """
    Inline admin for user subscriptions.
    """
    try:
        from subscriptions.models import Subscription
        model = Subscription
        extra = 0
        readonly_fields = ('created_at', 'updated_at')
        fields = ('plan', 'status', 'start_date', 'end_date', 'is_auto_renew', 'created_at')
    except ImportError:
        # If subscriptions app is not available, skip this inline
        pass

# Add the inline to UserAdmin if Subscription model is available
try:
    from subscriptions.models import Subscription
    UserAdmin.inlines = [SubscriptionInline]
except ImportError:
    pass