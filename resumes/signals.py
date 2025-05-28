from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Resume, ResumeVersion
from users.models import UserActivity


@receiver(post_save, sender=Resume)
def create_user_activity_on_resume_creation(sender, instance, created, **kwargs):
    """
    Create a user activity record when a new resume is created.
    """
    if created:
        UserActivity.objects.create(
            user=instance.user,
            activity_type='resume_creation',
            description=f'Created resume: {instance.title}'
        )


@receiver(post_save, sender=Resume)
def create_user_activity_on_resume_update(sender, instance, created, **kwargs):
    """
    Create a user activity record when a resume is updated.
    """
    if not created and kwargs.get('update_fields'):
        UserActivity.objects.create(
            user=instance.user,
            activity_type='resume_update',
            description=f'Updated resume: {instance.title}'
        )


@receiver(post_delete, sender=Resume)
def create_user_activity_on_resume_deletion(sender, instance, **kwargs):
    """
    Create a user activity record when a resume is deleted.
    """
    UserActivity.objects.create(
        user=instance.user,
        activity_type='resume_deletion',
        description=f'Deleted resume: {instance.title}'
    )


@receiver(post_save, sender=ResumeVersion)
def create_user_activity_on_version_creation(sender, instance, created, **kwargs):
    """
    Create a user activity record when a new resume version is created.
    """
    if created:
        UserActivity.objects.create(
            user=instance.resume.user,
            activity_type='resume_version_creation',
            description=f'Created version {instance.version_number} of resume: {instance.resume.title}'
        )