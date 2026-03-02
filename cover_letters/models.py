from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class CoverLetter(models.Model):
    """
    Model for AI-generated cover letters.

    Each cover letter is generated from a user's resume and a target job
    description. The NLP-based generator extracts relevant skills and
    experience from the resume and weaves them into a tailored letter.
    """

    TONE_CHOICES = (
        ('professional', 'Professional'),
        ('enthusiastic', 'Enthusiastic'),
        ('concise', 'Concise'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='cover_letters',
        verbose_name=_('User'),
    )
    resume = models.ForeignKey(
        'resumes.Resume',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cover_letters',
        verbose_name=_('Resume'),
    )
    job_title = models.CharField(_('Job Title'), max_length=255)
    company_name = models.CharField(_('Company Name'), max_length=255, blank=True)
    job_description = models.TextField(_('Job Description'))
    content = models.TextField(_('Cover Letter Content'))
    tone = models.CharField(
        _('Tone'),
        max_length=20,
        choices=TONE_CHOICES,
        default='professional',
    )
    is_edited = models.BooleanField(
        _('Is Edited'),
        default=False,
        help_text=_('Indicates whether the user has manually edited the generated content.'),
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Cover Letter')
        verbose_name_plural = _('Cover Letters')
        ordering = ['-created_at']

    def __str__(self):
        company = f" at {self.company_name}" if self.company_name else ""
        return f"{self.user.username} - {self.job_title}{company}"
