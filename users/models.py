from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid
import random
import string


class User(AbstractUser):
    """
    Custom User model for ResumeIt.
    Extends Django's AbstractUser to add additional fields.
    """
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('user', 'User'),
    )
    
    full_name = models.CharField(_('Full Name (as per Aadhaar)'), max_length=255, blank=True)
    role = models.CharField(_('Role'), max_length=10, choices=ROLE_CHOICES, default='user')
    is_verified = models.BooleanField(_('Email Verified'), default=False)
    phone_number = models.CharField(_('Phone Number'), max_length=15, blank=True)
    
    # OTP fields instead of token
    email_otp = models.CharField(_('Email OTP'), max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(_('OTP Created At'), blank=True, null=True)
    otp_attempts = models.IntegerField(_('OTP Attempts'), default=0)
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
    
    def __str__(self):
        return self.username
    
    def generate_otp(self):
        """
        Generate a 6-digit OTP for email verification.
        """
        self.email_otp = ''.join(random.choices(string.digits, k=6))
        self.otp_created_at = timezone.now()
        self.otp_attempts = 0
        self.save(update_fields=['email_otp', 'otp_created_at', 'otp_attempts'])
        return self.email_otp
    
    def is_otp_valid(self, otp):
        """
        Check if the provided OTP is valid and not expired.
        OTP expires after 10 minutes.
        """
        if not self.email_otp or not self.otp_created_at:
            return False
        
        # Check if OTP has expired (10 minutes)
        expiry_time = self.otp_created_at + timezone.timedelta(minutes=10)
        if timezone.now() > expiry_time:
            return False
        
        # Check if OTP matches
        return self.email_otp == otp
    
    def increment_otp_attempts(self):
        """
        Increment OTP attempts counter.
        """
        self.otp_attempts += 1
        self.save(update_fields=['otp_attempts'])
    
    def is_otp_attempts_exceeded(self):
        """
        Check if maximum OTP attempts (5) have been exceeded.
        """
        return self.otp_attempts >= 5
    
    def clear_otp(self):
        """
        Clear OTP data after successful verification or when generating new OTP.
        """
        self.email_otp = None
        self.otp_created_at = None
        self.otp_attempts = 0
        self.save(update_fields=['email_otp', 'otp_created_at', 'otp_attempts'])
    
    @property
    def is_subscribed(self):
        """
        Check if user has an active subscription.
        This is a property method that can be called like user.is_subscribed
        """
        return self.subscriptions.filter(
            status='active',
            end_date__gte=timezone.now().date()
        ).exists()
    
    @property
    def current_subscription(self):
        """
        Get the user's current active subscription.
        Returns None if no active subscription exists.
        """
        return self.subscriptions.filter(
            status='active',
            end_date__gte=timezone.now().date()
        ).first()
    
    def get_subscription_status(self):
        """
        Get detailed subscription status information.
        Returns a dictionary with subscription details.
        """
        current_sub = self.current_subscription
        
        if current_sub:
            return {
                'is_subscribed': True,
                'subscription_id': current_sub.id,
                'plan_name': current_sub.plan.name,
                'status': current_sub.status,
                'start_date': current_sub.start_date,
                'end_date': current_sub.end_date,
                'days_remaining': (current_sub.end_date - timezone.now().date()).days if current_sub.end_date else 0,
                'is_auto_renew': current_sub.is_auto_renew
            }
        
        return {
            'is_subscribed': False,
            'subscription_id': None,
            'plan_name': None,
            'status': None,
            'start_date': None,
            'end_date': None,
            'days_remaining': 0,
            'is_auto_renew': False
        }


class UserActivity(models.Model):
    """
    Model to track user activity for analytics.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(_('Activity Type'), max_length=50)
    description = models.TextField(_('Description'), blank=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('User Activity')
        verbose_name_plural = _('User Activities')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.activity_type}"


class Referral(models.Model):
    """
    Model to track referrals for the referral program.
    """
    referrer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referrals_made')
    referred = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referred_by', null=True, blank=True)
    code = models.CharField(_('Referral Code'), max_length=20, unique=True)
    is_successful = models.BooleanField(_('Is Successful'), default=False)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Referral')
        verbose_name_plural = _('Referrals')
    
    def __str__(self):
        referred_user = self.referred.username if self.referred else "Not yet registered"
        return f"{self.referrer.username} referred {referred_user}"