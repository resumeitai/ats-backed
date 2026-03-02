from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone


@shared_task
def send_otp_email_task(user_id):
    """Send OTP verification email asynchronously."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    try:
        user = User.objects.get(id=user_id)
        otp = user.email_otp

        if not otp:
            return

        subject = "Welcome to ResumeIt - Verify Your Email"
        message = (
            f"Hello {user.full_name or user.username},\n\n"
            f"Your OTP for email verification is: {otp}\n"
            f"This OTP will expire in 10 minutes.\n\n"
            f"Best regards,\nThe ResumeIt Team"
        )
        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #007bff; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .otp-box {{ background-color: #007bff; color: white; font-size: 28px; font-weight: bold;
                            text-align: center; padding: 25px; margin: 25px 0; border-radius: 8px; letter-spacing: 8px; }}
                .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
                .warning {{ background-color: #fff3cd; color: #856404; padding: 15px; border-radius: 5px; margin: 15px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header"><h1>Welcome to ResumeIt!</h1></div>
                <div class="content">
                    <h2>Hello {user.full_name or user.username},</h2>
                    <p>Your OTP for email verification is:</p>
                    <div class="otp-box">{otp}</div>
                    <div class="warning">
                        <strong>Important:</strong> This OTP will expire in 10 minutes.
                    </div>
                    <p>If you didn't create an account with us, please ignore this email.</p>
                </div>
                <div class="footer"><p>Best regards,<br>The ResumeIt Team</p></div>
            </div>
        </body>
        </html>
        """

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as e:
        print(f"Failed to send OTP email: {str(e)}")


@shared_task
def send_password_reset_email_task(user_id):
    """Send password reset OTP email asynchronously."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    try:
        user = User.objects.get(id=user_id)
        otp = user.password_reset_otp

        if not otp:
            return

        subject = "Password Reset OTP - ResumeIt"
        message = f"Your password reset OTP is: {otp}\nThis OTP will expire in 10 minutes."
        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #dc3545; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .otp-box {{ background-color: #dc3545; color: white; font-size: 24px; font-weight: bold;
                            text-align: center; padding: 20px; margin: 20px 0; border-radius: 5px; letter-spacing: 5px; }}
                .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
                .warning {{ background-color: #fff3cd; color: #856404; padding: 15px; border-radius: 5px; margin: 15px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header"><h1>Password Reset</h1></div>
                <div class="content">
                    <h2>Hello {user.full_name or user.username},</h2>
                    <p>We received a request to reset your password. Use the OTP below:</p>
                    <div class="otp-box">{otp}</div>
                    <div class="warning">
                        <strong>Important:</strong> This OTP will expire in 10 minutes.
                    </div>
                    <p>If you didn't request a password reset, please ignore this email.</p>
                </div>
                <div class="footer"><p>Best regards,<br>The ResumeIt Team</p></div>
            </div>
        </body>
        </html>
        """

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as e:
        print(f"Failed to send password reset email: {str(e)}")


@shared_task
def cleanup_expired_otps_task():
    """Periodic task to clear expired OTPs (older than 10 minutes)."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    threshold = timezone.now() - timezone.timedelta(minutes=10)
    updated = User.objects.filter(
        otp_created_at__lt=threshold,
        email_otp__isnull=False,
    ).update(email_otp=None, otp_created_at=None, otp_attempts=0)

    updated += User.objects.filter(
        password_reset_otp_created_at__lt=threshold,
        password_reset_otp__isnull=False,
    ).update(password_reset_otp=None, password_reset_otp_created_at=None)

    return f"Cleaned up {updated} expired OTPs"
