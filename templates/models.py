from django.db import models
from django.utils.translation import gettext_lazy as _


class TemplateCategory(models.Model):
    """
    Model for template categories (industry/profession).
    """
    name = models.CharField(_('Category Name'), max_length=100)
    description = models.TextField(_('Description'), blank=True)
    
    class Meta:
        verbose_name = _('Template Category')
        verbose_name_plural = _('Template Categories')
    
    def __str__(self):
        return self.name


class Template(models.Model):
    """
    Model for resume templates.
    """
    name = models.CharField(_('Template Name'), max_length=100)
    description = models.TextField(_('Description'), blank=True)
    category = models.ForeignKey(TemplateCategory, on_delete=models.SET_NULL, null=True, related_name='templates')
    thumbnail = models.ImageField(_('Thumbnail'), upload_to='templates/thumbnails/', blank=True)
    html_structure = models.TextField(_('HTML Structure'))
    css_styles = models.TextField(_('CSS Styles'), blank=True)
    is_premium = models.BooleanField(_('Is Premium'), default=False)
    is_active = models.BooleanField(_('Is Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Template')
        verbose_name_plural = _('Templates')
    
    def __str__(self):
        return self.name


class TemplateSection(models.Model):
    """
    Model for template sections.
    """
    template = models.ForeignKey(Template, on_delete=models.CASCADE, related_name='sections')
    name = models.CharField(_('Section Name'), max_length=100)
    html_id = models.CharField(_('HTML ID'), max_length=100)
    order = models.PositiveIntegerField(_('Display Order'), default=0)
    is_required = models.BooleanField(_('Is Required'), default=False)
    
    class Meta:
        verbose_name = _('Template Section')
        verbose_name_plural = _('Template Sections')
        ordering = ['order']
    
    def __str__(self):
        return f"{self.template.name} - {self.name}"