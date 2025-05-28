from django.contrib import admin
from .models import TemplateCategory, Template, TemplateSection


class TemplateSectionInline(admin.TabularInline):
    """
    Inline admin for TemplateSection model.
    """
    model = TemplateSection
    extra = 1


@admin.register(TemplateCategory)
class TemplateCategoryAdmin(admin.ModelAdmin):
    """
    Admin configuration for the TemplateCategory model.
    """
    list_display = ('name', 'description')
    search_fields = ('name', 'description')


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Template model.
    """
    list_display = ('name', 'category', 'is_premium', 'is_active', 'created_at', 'updated_at')
    list_filter = ('category', 'is_premium', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [TemplateSectionInline]


@admin.register(TemplateSection)
class TemplateSectionAdmin(admin.ModelAdmin):
    """
    Admin configuration for the TemplateSection model.
    """
    list_display = ('name', 'template', 'html_id', 'order', 'is_required')
    list_filter = ('template', 'is_required')
    search_fields = ('name', 'html_id', 'template__name')