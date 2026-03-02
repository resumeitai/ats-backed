from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class JobApplication(models.Model):
    """
    Model for tracking job applications in a Kanban-style board.
    """
    WORK_TYPE_CHOICES = (
        ('remote', 'Remote'),
        ('onsite', 'Onsite'),
        ('hybrid', 'Hybrid'),
    )

    STATUS_CHOICES = (
        ('wishlist', 'Wishlist'),
        ('applied', 'Applied'),
        ('phone_screen', 'Phone Screen'),
        ('interview', 'Interview'),
        ('technical', 'Technical'),
        ('offer', 'Offer'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    )

    PRIORITY_CHOICES = (
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='job_applications',
        verbose_name=_('User'),
    )
    resume = models.ForeignKey(
        'resumes.Resume',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='job_applications',
        verbose_name=_('Resume'),
    )
    cover_letter = models.ForeignKey(
        'cover_letters.CoverLetter',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='job_applications',
        verbose_name=_('Cover Letter'),
    )
    job_title = models.CharField(_('Job Title'), max_length=255)
    company_name = models.CharField(_('Company Name'), max_length=255)
    job_url = models.URLField(_('Job URL'), blank=True)
    job_description = models.TextField(_('Job Description'), blank=True)
    salary_min = models.DecimalField(
        _('Minimum Salary'),
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    salary_max = models.DecimalField(
        _('Maximum Salary'),
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    location = models.CharField(_('Location'), max_length=255, blank=True)
    work_type = models.CharField(
        _('Work Type'),
        max_length=10,
        choices=WORK_TYPE_CHOICES,
        default='onsite',
    )
    status = models.CharField(
        _('Status'),
        max_length=15,
        choices=STATUS_CHOICES,
        default='wishlist',
    )
    priority = models.CharField(
        _('Priority'),
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium',
    )
    applied_date = models.DateField(_('Applied Date'), null=True, blank=True)
    response_date = models.DateField(_('Response Date'), null=True, blank=True)
    notes = models.TextField(_('Notes'), blank=True)
    contact_name = models.CharField(_('Contact Name'), max_length=255, blank=True)
    contact_email = models.EmailField(_('Contact Email'), blank=True)
    source = models.CharField(
        _('Source'),
        max_length=255,
        blank=True,
        help_text=_('e.g. LinkedIn, Indeed, Referral'),
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Job Application')
        verbose_name_plural = _('Job Applications')
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.job_title} at {self.company_name} ({self.get_status_display()})"


class InterviewRound(models.Model):
    """
    Model for tracking individual interview rounds within a job application.
    """
    TYPE_CHOICES = (
        ('phone', 'Phone'),
        ('video', 'Video'),
        ('onsite', 'Onsite'),
        ('technical', 'Technical'),
        ('behavioral', 'Behavioral'),
        ('panel', 'Panel'),
    )

    STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rescheduled', 'Rescheduled'),
    )

    application = models.ForeignKey(
        JobApplication,
        on_delete=models.CASCADE,
        related_name='interview_rounds',
        verbose_name=_('Application'),
    )
    round_number = models.PositiveIntegerField(_('Round Number'))
    type = models.CharField(
        _('Interview Type'),
        max_length=15,
        choices=TYPE_CHOICES,
    )
    scheduled_at = models.DateTimeField(_('Scheduled At'), null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(
        _('Duration (minutes)'),
        null=True,
        blank=True,
    )
    interviewer = models.CharField(_('Interviewer'), max_length=255, blank=True)
    notes = models.TextField(_('Notes'), blank=True)
    feedback = models.TextField(_('Feedback'), blank=True)
    status = models.CharField(
        _('Status'),
        max_length=15,
        choices=STATUS_CHOICES,
        default='scheduled',
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)

    class Meta:
        verbose_name = _('Interview Round')
        verbose_name_plural = _('Interview Rounds')
        ordering = ['round_number']

    def __str__(self):
        return (
            f"Round {self.round_number} - {self.get_type_display()} "
            f"for {self.application.job_title}"
        )


class ApplicationNote(models.Model):
    """
    Model for activity notes / timeline entries on a job application.
    """
    application = models.ForeignKey(
        JobApplication,
        on_delete=models.CASCADE,
        related_name='activity_notes',
        verbose_name=_('Application'),
    )
    note = models.TextField(_('Note'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)

    class Meta:
        verbose_name = _('Application Note')
        verbose_name_plural = _('Application Notes')
        ordering = ['-created_at']

    def __str__(self):
        return f"Note on {self.application.job_title} - {self.created_at:%Y-%m-%d %H:%M}"
