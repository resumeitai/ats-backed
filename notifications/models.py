from django.db import models
from django.conf import settings


class Notification(models.Model):
    """
    Model to store in-app notifications for users.
    """
    NOTIFICATION_TYPES = (
        ('welcome', 'Welcome'),
        ('ats_result', 'ATS Result'),
        ('subscription_expiry', 'Subscription Expiry'),
        ('subscription_activated', 'Subscription Activated'),
        ('password_changed', 'Password Changed'),
        ('system', 'System'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f"{self.user.username} - {self.title}"


class EmailTemplate(models.Model):
    """
    Model to store reusable email templates for outbound emails.
    """
    name = models.CharField(max_length=100, unique=True)
    subject = models.CharField(max_length=255)
    html_body = models.TextField()
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Email Template'
        verbose_name_plural = 'Email Templates'

    def __str__(self):
        return self.name
