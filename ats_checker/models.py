from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class ATSScore(models.Model):
    """
    Model for storing ATS scores for resumes.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ats_scores')
    resume = models.ForeignKey('resumes.Resume', on_delete=models.CASCADE, related_name='ats_scores')
    job_title = models.CharField(_('Job Title'), max_length=255)
    job_description = models.TextField(_('Job Description'))
    score = models.PositiveIntegerField(_('ATS Score'), help_text='Score out of 100')
    analysis = models.JSONField(_('Analysis Results'), default=dict)
    suggestions = models.JSONField(_('Improvement Suggestions'), default=list)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('ATS Score')
        verbose_name_plural = _('ATS Scores')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.resume.title} - {self.score}%"


class KeywordMatch(models.Model):
    """
    Model for tracking keyword matches between resumes and job descriptions.
    """
    ats_score = models.ForeignKey(ATSScore, on_delete=models.CASCADE, related_name='keyword_matches')
    keyword = models.CharField(_('Keyword'), max_length=100)
    found = models.BooleanField(_('Found in Resume'), default=False)
    importance = models.CharField(_('Importance'), max_length=20, choices=[
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ])
    context = models.TextField(_('Context in Resume'), blank=True)
    
    class Meta:
        verbose_name = _('Keyword Match')
        verbose_name_plural = _('Keyword Matches')
    
    def __str__(self):
        return f"{self.keyword} - {'Found' if self.found else 'Not Found'}"


class OptimizationSuggestion(models.Model):
    """
    Model for storing optimization suggestions for resumes.
    """
    ats_score = models.ForeignKey(ATSScore, on_delete=models.CASCADE, related_name='optimization_suggestions')
    section = models.CharField(_('Resume Section'), max_length=100)
    original_text = models.TextField(_('Original Text'), blank=True)
    suggested_text = models.TextField(_('Suggested Text'), blank=True)
    reason = models.TextField(_('Reason for Suggestion'))
    applied = models.BooleanField(_('Applied to Resume'), default=False)
    
    class Meta:
        verbose_name = _('Optimization Suggestion')
        verbose_name_plural = _('Optimization Suggestions')
    
    def __str__(self):
        return f"Suggestion for {self.section}"


class JobTitleSynonym(models.Model):
    """
    Model for storing job title synonyms to improve matching.
    """
    title = models.CharField(_('Job Title'), max_length=255, unique=True)
    synonyms = models.JSONField(_('Synonyms'), default=list)
    
    class Meta:
        verbose_name = _('Job Title Synonym')
        verbose_name_plural = _('Job Title Synonyms')
    
    def __str__(self):
        return self.title