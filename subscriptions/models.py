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
    trial_days = models.PositiveIntegerField(_('Trial Days'), default=0)
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

    PAYMENT_GATEWAY_CHOICES = (
        ('razorpay', 'Razorpay'),
        ('stripe', 'Stripe'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, related_name='transactions')
    amount = models.DecimalField(_('Amount'), max_digits=10, decimal_places=2)
    currency = models.CharField(_('Currency'), max_length=3, default='INR')
    payment_method = models.CharField(_('Payment Method'), max_length=20, choices=PAYMENT_METHOD_CHOICES)
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(_('Transaction ID'), max_length=100, blank=True)
    payment_gateway = models.CharField(_('Payment Gateway'), max_length=20, choices=PAYMENT_GATEWAY_CHOICES, default='razorpay')
    gateway_order_id = models.CharField(_('Gateway Order ID'), max_length=100, blank=True)
    refund_id = models.CharField(_('Refund ID'), max_length=100, blank=True)
    refund_amount = models.DecimalField(_('Refund Amount'), max_digits=10, decimal_places=2, null=True, blank=True)
    refund_status = models.CharField(_('Refund Status'), max_length=20, blank=True)
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


class PromotionalOffer(models.Model):
    """
    Model for promotional offers / promo codes.
    """
    code = models.CharField(_('Promo Code'), max_length=50, unique=True)
    discount_percentage = models.PositiveIntegerField(_('Discount Percentage'))
    valid_from = models.DateTimeField(_('Valid From'))
    valid_until = models.DateTimeField(_('Valid Until'))
    max_uses = models.PositiveIntegerField(_('Max Uses'), default=100)
    current_uses = models.PositiveIntegerField(_('Current Uses'), default=0)
    applicable_plans = models.ManyToManyField(SubscriptionPlan, related_name='promotional_offers', blank=True)
    is_active = models.BooleanField(_('Is Active'), default=True)

    class Meta:
        verbose_name = _('Promotional Offer')
        verbose_name_plural = _('Promotional Offers')

    def __str__(self):
        return f"{self.code} - {self.discount_percentage}% off"


class Invoice(models.Model):
    """
    Model for invoices linked to transactions.
    """
    transaction = models.OneToOneField(Transaction, on_delete=models.CASCADE, related_name='invoice')
    invoice_number = models.CharField(_('Invoice Number'), max_length=50, unique=True)
    pdf_file = models.FileField(_('PDF File'), upload_to='invoices/', blank=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)

    class Meta:
        verbose_name = _('Invoice')
        verbose_name_plural = _('Invoices')

    def __str__(self):
        return f"Invoice {self.invoice_number}"