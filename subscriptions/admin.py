from django.contrib import admin
from .models import SubscriptionPlan, Subscription, Transaction, ReferralBonus


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    """
    Admin configuration for the SubscriptionPlan model.
    """
    list_display = ('name', 'price', 'duration_months', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'duration_months', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Subscription model.
    """
    list_display = ('user', 'plan', 'status', 'start_date', 'end_date', 'is_auto_renew', 'created_at')
    list_filter = ('status', 'is_auto_renew', 'start_date', 'end_date', 'created_at')
    search_fields = ('user__username', 'user__email', 'plan__name')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('user', 'plan')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Transaction model.
    """
    list_display = ('user', 'subscription', 'amount', 'currency', 'payment_method', 'status', 'created_at')
    list_filter = ('status', 'payment_method', 'currency', 'created_at')
    search_fields = ('user__username', 'user__email', 'transaction_id')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('user', 'subscription')


@admin.register(ReferralBonus)
class ReferralBonusAdmin(admin.ModelAdmin):
    """
    Admin configuration for the ReferralBonus model.
    """
    list_display = ('referrer', 'bonus_months', 'is_applied', 'created_at')
    list_filter = ('is_applied', 'bonus_months', 'created_at')
    search_fields = ('referrer__username', 'referrer__email')
    readonly_fields = ('created_at',)
    raw_id_fields = ('referrer', 'referral', 'subscription')