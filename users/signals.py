from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from .models import UserActivity, Referral

User = get_user_model()


@receiver(post_save, sender=User)
def send_otp_on_registration(sender, instance, created, **kwargs):
    """
    Send OTP email when a new user is registered.
    """
    if created and instance.email:
        # Generate OTP for the new user
        otp = instance.generate_otp()
        
        subject = "Welcome to ResumeIt - Verify Your Email"
        message = f"""
        Hello {instance.full_name or instance.username},
        
        Welcome to ResumeIt! To complete your registration, please verify your email address using the OTP below:
        
        Your OTP: {otp}
        
        This OTP will expire in 10 minutes.
        
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
                .otp-box {{ background-color: #007bff; color: white; font-size: 28px; font-weight: bold; text-align: center; padding: 25px; margin: 25px 0; border-radius: 8px; letter-spacing: 8px; }}
                .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
                .welcome {{ background-color: #d4edda; color: #155724; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                .warning {{ background-color: #fff3cd; color: #856404; padding: 15px; border-radius: 5px; margin: 15px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to ResumeIt!</h1>
                </div>
                <div class="content">
                    <div class="welcome">
                        <h2>🎉 Welcome {instance.full_name or instance.username}!</h2>
                        <p>Thank you for joining ResumeIt. We're excited to help you create amazing resumes!</p>
                    </div>
                    
                    <h3>Verify Your Email Address</h3>
                    <p>To complete your registration and secure your account, please use the OTP below:</p>
                    
                    <div class="otp-box">{otp}</div>
                    
                    <div class="warning">
                        <strong>⏰ Important:</strong> This OTP will expire in 10 minutes. Please verify your email as soon as possible.
                    </div>
                    
                    <p>Enter this OTP in the verification form to activate your account and start using ResumeIt.</p>
                    
                    <p>If you didn't create an account with us, please ignore this email.</p>
                </div>
                <div class="footer">
                    <p>Best regards,<br>The ResumeIt Team</p>
                    <p><small>This is an automated email. Please do not reply to this message.</small></p>
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
            print(f"Failed to send OTP email to {instance.email}: {str(e)}")


@receiver(post_save, sender=User)
def create_user_activity_on_registration(sender, instance, created, **kwargs):
    """
    Create a user activity record when a new user is registered.
    """
    if created:
        UserActivity.objects.create(
            user=instance,
            activity_type='registration',
            description='User registered and OTP sent'
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