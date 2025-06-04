from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from .models import UserActivity, Referral

User = get_user_model()


@receiver(post_save, sender=User)
def send_email_verification_on_registration(sender, instance, created, **kwargs):
    """
    Send email verification when a new user is registered.
    """
    if created and instance.email:
        verification_url = f"{settings.FRONTEND_URL}/verify-email/{instance.email_verification_token}/"
        
        subject = "Verify Your Email - ResumeIt"
        message = f"""
        Hello {instance.full_name or instance.username},
        
        Welcome to ResumeIt! Please verify your email address by clicking the link below:
        
        {verification_url}
        
        If you didn't create an account with us, please ignore this email.
        
        Best regards,
        The ResumeIt Team
        """
        
        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #007bff; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .button {{ display: inline-block; padding: 12px 24px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to ResumeIt!</h1>
                </div>
                <div class="content">
                    <h2>Hello {instance.full_name or instance.username},</h2>
                    <p>Thank you for registering with ResumeIt. To complete your registration, please verify your email address by clicking the button below:</p>
                    <a href="{verification_url}" class="button">Verify Email Address</a>
                    <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
                    <p><a href="{verification_url}">{verification_url}</a></p>
                    <p>If you didn't create an account with us, please ignore this email.</p>
                </div>
                <div class="footer">
                    <p>Best regards,<br>The ResumeIt Team</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[instance.email],
                html_message=html_message,
                fail_silently=False,
            )
        except Exception as e:
            print(f"Failed to send verification email to {instance.email}: {str(e)}")


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