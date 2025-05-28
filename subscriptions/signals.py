from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from .models import Subscription, Transaction, ReferralBonus
from users.models import UserActivity


@receiver(post_save, sender=Subscription)
def create_user_activity_on_subscription_change(sender, instance, created, **kwargs):
    """
    Create a user activity record when a subscription is created or updated.
    """
    if created:
        UserActivity.objects.create(
            user=instance.user,
            activity_type='subscription_created',
            description=f'Subscription to {instance.plan.name} created'
        )
    elif not created and kwargs.get('update_fields'):
        UserActivity.objects.create(
            user=instance.user,
            activity_type='subscription_updated',
            description=f'Subscription to {instance.plan.name} updated'
        )


@receiver(pre_save, sender=Subscription)
def update_subscription_dates(sender, instance, **kwargs):
    """
    Update subscription dates when status changes.
    """
    if not instance.pk:
        # New subscription
        return
    
    try:
        old_instance = Subscription.objects.get(pk=instance.pk)
        
        # If status changed to active and wasn't active before
        if instance.status == 'active' and old_instance.status != 'active':
            # Set start date to today if not already set
            if not instance.start_date:
                instance.start_date = timezone.now().date()
            
            # Set end date based on plan duration
            if instance.plan and instance.plan.duration_months:
                instance.end_date = instance.start_date + timedelta(days=30 * instance.plan.duration_months)
        
        # If status changed to cancelled
        elif instance.status == 'cancelled' and old_instance.status != 'cancelled':
            # End date remains the same, we just mark it as cancelled
            pass
        
        # If status changed to expired
        elif instance.status == 'expired' and old_instance.status != 'expired':
            # End date should be today
            instance.end_date = timezone.now().date()
    
    except Subscription.DoesNotExist:
        pass


@receiver(post_save, sender=Transaction)
def update_subscription_on_transaction_completion(sender, instance, created, **kwargs):
    """
    Update subscription when a transaction is completed.
    """
    if not created and instance.status == 'completed' and instance.subscription:
        subscription = instance.subscription
        
        # If subscription is pending or expired, activate it
        if subscription.status in ['pending', 'expired', 'cancelled']:
            subscription.status = 'active'
            
            # Set start date to today
            subscription.start_date = timezone.now().date()
            
            # Set end date based on plan duration
            if subscription.plan and subscription.plan.duration_months:
                subscription.end_date = subscription.start_date + timedelta(days=30 * subscription.plan.duration_months)
            
            subscription.save()
        
        # Create user activity
        UserActivity.objects.create(
            user=instance.user,
            activity_type='payment_completed',
            description=f'Payment of {instance.amount} {instance.currency} completed for {subscription.plan.name}'
        )


@receiver(post_save, sender=ReferralBonus)
def apply_referral_bonus(sender, instance, created, **kwargs):
    """
    Apply referral bonus to subscription when created.
    """
    if created and instance.subscription and not instance.is_applied:
        subscription = instance.subscription
        
        # If subscription is active, extend its end date
        if subscription.status == 'active' and subscription.end_date:
            subscription.end_date = subscription.end_date + timedelta(days=30 * instance.bonus_months)
            subscription.save()
            
            # Mark bonus as applied
            instance.is_applied = True
            instance.save(update_fields=['is_applied'])
            
            # Create user activity
            UserActivity.objects.create(
                user=instance.referrer,
                activity_type='referral_bonus_applied',
                description=f'Referral bonus of {instance.bonus_months} months applied to subscription'
            )