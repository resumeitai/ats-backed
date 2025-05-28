from django.contrib import admin
from .models import ATSScore, KeywordMatch, OptimizationSuggestion, JobTitleSynonym


class KeywordMatchInline(admin.TabularInline):
    """
    Inline admin for KeywordMatch model.
    """
    model = KeywordMatch
    extra = 0


class OptimizationSuggestionInline(admin.TabularInline):
    """
    Inline admin for OptimizationSuggestion model.
    """
    model = OptimizationSuggestion
    extra = 0


@admin.register(ATSScore)
class ATSScoreAdmin(admin.ModelAdmin):
    """
    Admin configuration for the ATSScore model.
    """
    list_display = ('user', 'resume', 'job_title', 'score', 'created_at', 'updated_at')
    list_filter = ('score', 'created_at', 'user')
    search_fields = ('user__username', 'user__email', 'resume__title', 'job_title')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [KeywordMatchInline, OptimizationSuggestionInline]
    
    fieldsets = (
        (None, {
            'fields': ('user', 'resume', 'job_title', 'score')
        }),
        ('Job Description', {
            'fields': ('job_description',),
            'classes': ('collapse',),
        }),
        ('Analysis', {
            'fields': ('analysis', 'suggestions'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(KeywordMatch)
class KeywordMatchAdmin(admin.ModelAdmin):
    """
    Admin configuration for the KeywordMatch model.
    """
    list_display = ('keyword', 'ats_score', 'found', 'importance')
    list_filter = ('found', 'importance')
    search_fields = ('keyword', 'ats_score__job_title', 'ats_score__user__username')


@admin.register(OptimizationSuggestion)
class OptimizationSuggestionAdmin(admin.ModelAdmin):
    """
    Admin configuration for the OptimizationSuggestion model.
    """
    list_display = ('section', 'ats_score', 'applied')
    list_filter = ('applied', 'section')
    search_fields = ('section', 'reason', 'ats_score__job_title', 'ats_score__user__username')


@admin.register(JobTitleSynonym)
class JobTitleSynonymAdmin(admin.ModelAdmin):
    """
    Admin configuration for the JobTitleSynonym model.
    """
    list_display = ('title',)
    search_fields = ('title', 'synonyms')