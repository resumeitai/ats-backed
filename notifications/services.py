from .models import Notification


def create_notification(user, type, title, message, data=None):
    """
    Create and return a Notification instance for the given user.

    Args:
        user: The User instance to notify.
        type: One of the NOTIFICATION_TYPES choices.
        title: Short headline for the notification.
        message: Full notification body text.
        data: Optional dict of extra metadata stored as JSON.

    Returns:
        The newly created Notification object.
    """
    return Notification.objects.create(
        user=user,
        type=type,
        title=title,
        message=message,
        data=data or {},
    )


def send_welcome_notification(user):
    """
    Create a welcome notification for a newly registered user.
    """
    return create_notification(
        user=user,
        type='welcome',
        title='Welcome to ResumeIt!',
        message=(
            f'Hi {user.full_name or user.username}, welcome to ResumeIt! '
            'Start building your ATS-optimised resume today and land your dream job.'
        ),
    )


def send_ats_result_notification(user, ats_score):
    """
    Notify the user about their ATS score result.

    Args:
        user: The User instance.
        ats_score: Numeric ATS compatibility score.
    """
    return create_notification(
        user=user,
        type='ats_result',
        title='Your ATS Score is Ready',
        message=(
            f'Your resume has been analysed. You scored {ats_score}% on '
            'ATS compatibility. Check the detailed report for improvement tips.'
        ),
        data={'ats_score': ats_score},
    )


def send_subscription_expiry_notification(user, days_remaining):
    """
    Warn the user that their subscription is about to expire.

    Args:
        user: The User instance.
        days_remaining: Number of days until the subscription expires.
    """
    return create_notification(
        user=user,
        type='subscription_expiry',
        title='Subscription Expiring Soon',
        message=(
            f'Your subscription will expire in {days_remaining} '
            f'day{"s" if days_remaining != 1 else ""}. '
            'Renew now to continue enjoying premium features.'
        ),
        data={'days_remaining': days_remaining},
    )


def send_subscription_activated_notification(user, plan_name):
    """
    Notify the user that their subscription has been activated.

    Args:
        user: The User instance.
        plan_name: Name of the subscription plan that was activated.
    """
    return create_notification(
        user=user,
        type='subscription_activated',
        title='Subscription Activated',
        message=(
            f'Your {plan_name} plan has been activated successfully. '
            'Enjoy all the premium features of ResumeIt!'
        ),
        data={'plan_name': plan_name},
    )
