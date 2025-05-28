from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserActivity, Referral

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_activity_on_registration(sender, instance, created, **kwargs):
    """
    Create a user activity record when a new user is registered.
    """
    if created:
        UserActivity.objects.create(
            user=instance,
            activity_type='registration',
            description='User registered'
        )


@receiver(post_save, sender=User)
def check_referral_on_registration(sender, instance, created, **kwargs):
    """
    Check if the user was referred and update the referral record.
    """
    if created and instance.email:
        # Check if there's a referral with this email
        referrals = Referral.objects.filter(code__isnull=False, is_successful=False)
        
        for referral in referrals:
            # If a referral is found, mark it as successful
            if referral.referred is None:
                referral.referred = instance
                referral.is_successful = True
                referral.save()
                
                # Create activity for both users
                UserActivity.objects.create(
                    user=referral.referrer,
                    activity_type='referral_successful',
                    description=f'Referral for {instance.email} was successful'
                )
                
                UserActivity.objects.create(
                    user=instance,
                    activity_type='referred_by',
                    description=f'Referred by {referral.referrer.email}'
                )
                
                # Only process the first matching referral
                break


@receiver(post_save, sender=User)
def track_user_profile_update(sender, instance, created, **kwargs):
    """
    Track when a user updates their profile.
    """
    if not created and kwargs.get('update_fields'):
        UserActivity.objects.create(
            user=instance,
            activity_type='profile_update',
            description='User updated their profile'
        )