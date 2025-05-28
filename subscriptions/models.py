from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class SubscriptionPlan(models.Model):
    """
    Model for subscription plans.
    """
    name = models.CharField(_('Plan Name'), max_length=100)
    description = models.TextField(_('Description'), blank=True)
    price = models.DecimalField(_('Price'), max_digits=10, decimal_places=2)
    duration_months = models.PositiveIntegerField(_('Duration (months)'))
    features = models.JSONField(_('Features'), default=list)
    is_active = models.BooleanField(_('Is Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Subscription Plan')
        verbose_name_plural = _('Subscription Plans')
    
    def __str__(self):
        return f"{self.name} - {self.duration_months} months"


class Subscription(models.Model):
    """
    Model for user subscriptions.
    """
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('pending', 'Pending'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name='subscriptions')
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='pending')
    start_date = models.DateField(_('Start Date'), null=True, blank=True)
    end_date = models.DateField(_('End Date'), null=True, blank=True)
    is_auto_renew = models.BooleanField(_('Auto Renew'), default=False)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Subscription')
        verbose_name_plural = _('Subscriptions')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.plan.name} ({self.status})"


class Transaction(models.Model):
    """
    Model for payment transactions.
    """
    PAYMENT_METHOD_CHOICES = (
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('upi', 'UPI'),
        ('net_banking', 'Net Banking'),
        ('wallet', 'Wallet'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, related_name='transactions')
    amount = models.DecimalField(_('Amount'), max_digits=10, decimal_places=2)
    currency = models.CharField(_('Currency'), max_length=3, default='INR')
    payment_method = models.CharField(_('Payment Method'), max_length=20, choices=PAYMENT_METHOD_CHOICES)
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(_('Transaction ID'), max_length=100, blank=True)
    payment_gateway_response = models.JSONField(_('Payment Gateway Response'), default=dict, blank=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Transaction')
        verbose_name_plural = _('Transactions')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.amount} {self.currency} ({self.status})"


class ReferralBonus(models.Model):
    """
    Model for tracking referral bonuses.
    """
    referrer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referral_bonuses')
    referral = models.ForeignKey('users.Referral', on_delete=models.CASCADE, related_name='bonuses')
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, related_name='referral_bonuses')
    bonus_months = models.PositiveIntegerField(_('Bonus Months'), default=6)
    is_applied = models.BooleanField(_('Is Applied'), default=False)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Referral Bonus')
        verbose_name_plural = _('Referral Bonuses')
    
    def __str__(self):
        return f"{self.referrer.username} - {self.bonus_months} months bonus"