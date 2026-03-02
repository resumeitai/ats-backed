from celery import shared_task
from django.utils import timezone


@shared_task
def check_subscription_renewals_task():
    """Check and expire overdue subscriptions. Auto-renew if enabled."""
    from .models import Subscription

    today = timezone.now().date()
    expired = Subscription.objects.filter(
        status='active',
        end_date__lt=today,
    )

    renewed_count = 0
    expired_count = 0

    for sub in expired:
        if sub.is_auto_renew:
            # For auto-renew, we'd create a new transaction and process payment
            # For now, just extend the subscription
            from datetime import timedelta
            sub.start_date = today
            sub.end_date = today + timedelta(days=30 * sub.plan.duration_months)
            sub.save()
            renewed_count += 1
        else:
            sub.status = 'expired'
            sub.save()
            expired_count += 1

    return f"Renewed: {renewed_count}, Expired: {expired_count}"


@shared_task
def send_subscription_expiry_reminder_task():
    """Send reminders to users whose subscriptions expire within 3 days."""
    from .models import Subscription
    from users.models import UserActivity

    today = timezone.now().date()
    from datetime import timedelta
    expiring_soon = Subscription.objects.filter(
        status='active',
        end_date__lte=today + timedelta(days=3),
        end_date__gte=today,
    ).select_related('user', 'plan')

    count = 0
    for sub in expiring_soon:
        days_left = (sub.end_date - today).days
        UserActivity.objects.create(
            user=sub.user,
            activity_type='subscription_expiry_reminder',
            description=f'Your {sub.plan.name} subscription expires in {days_left} day(s).'
        )
        count += 1

    return f"Sent {count} expiry reminders"
