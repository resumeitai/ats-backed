from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class Resume(models.Model):
    """
    Model for user resumes.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='resumes')
    template = models.ForeignKey('templates.Template', on_delete=models.SET_NULL, null=True, related_name='resumes')
    title = models.CharField(_('Resume Title'), max_length=255)
    content = models.JSONField(_('Resume Content'), default=dict)
    is_active = models.BooleanField(_('Is Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Resume')
        verbose_name_plural = _('Resumes')
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"


class ResumeVersion(models.Model):
    """
    Model for tracking resume versions.
    """
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='versions')
    content = models.JSONField(_('Resume Content'), default=dict)
    version_number = models.PositiveIntegerField(_('Version Number'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Resume Version')
        verbose_name_plural = _('Resume Versions')
        ordering = ['-version_number']
        unique_together = ['resume', 'version_number']
    
    def __str__(self):
        return f"{self.resume.title} - v{self.version_number}"


class ResumeSection(models.Model):
    """
    Model for defining resume sections.
    """
    SECTION_TYPES = (
        ('personal', 'Personal Information'),
        ('education', 'Education'),
        ('experience', 'Work Experience'),
        ('skills', 'Skills'),
        ('projects', 'Projects'),
        ('certifications', 'Certifications'),
        ('custom', 'Custom Section'),
    )
    
    name = models.CharField(_('Section Name'), max_length=100)
    type = models.CharField(_('Section Type'), max_length=20, choices=SECTION_TYPES)
    is_required = models.BooleanField(_('Is Required'), default=False)
    order = models.PositiveIntegerField(_('Display Order'), default=0)
    
    class Meta:
        verbose_name = _('Resume Section')
        verbose_name_plural = _('Resume Sections')
        ordering = ['order']
    
    def __str__(self):
        return self.name