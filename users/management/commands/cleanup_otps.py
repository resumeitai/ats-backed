from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class Command(BaseCommand):
    help = 'Delete expired OTPs (older than 10 minutes)'

    def handle(self, *args, **options):
        threshold = timezone.now() - timezone.timedelta(minutes=10)

        email_count = User.objects.filter(
            otp_created_at__lt=threshold,
            email_otp__isnull=False,
        ).update(email_otp=None, otp_created_at=None, otp_attempts=0)

        reset_count = User.objects.filter(
            password_reset_otp_created_at__lt=threshold,
            password_reset_otp__isnull=False,
        ).update(password_reset_otp=None, password_reset_otp_created_at=None)

        self.stdout.write(self.style.SUCCESS(
            f'Cleaned up {email_count} expired email OTPs and {reset_count} expired password reset OTPs'
        ))
