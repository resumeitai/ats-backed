from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserActivity, Referral

User = get_user_model()


@receiver(post_save, sender=User)
def send_otp_on_registration(sender, instance, created, **kwargs):
    """Send OTP email when a new user is registered (via Celery)."""
    if created and instance.email:
        instance.generate_otp()

        from .tasks import send_otp_email_task
        send_otp_email_task.delay(instance.id)


@receiver(post_save, sender=User)
def create_user_activity_on_registration(sender, instance, created, **kwargs):
    """Create a user activity record when a new user is registered."""
    if created:
        UserActivity.objects.create(
            user=instance,
            activity_type='registration',
            description='User registered and OTP sent'
        )


@receiver(post_save, sender=User)
def check_referral_on_registration(sender, instance, created, **kwargs):
    """Check if the user was referred and update the referral record."""
    if created and instance.email:
        referrals = Referral.objects.filter(code__isnull=False, is_successful=False)

        for referral in referrals:
            if referral.referred is None:
                referral.referred = instance
                referral.is_successful = True
                referral.save()

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
                break


@receiver(post_save, sender=User)
def track_user_profile_update(sender, instance, created, **kwargs):
    """Track when a user updates their profile."""
    if not created and kwargs.get('update_fields'):
        UserActivity.objects.create(
            user=instance,
            activity_type='profile_update',
            description='User updated their profile'
        )
