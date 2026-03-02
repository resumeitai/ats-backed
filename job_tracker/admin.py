from django.contrib import admin
from .models import JobApplication, InterviewRound, ApplicationNote


class InterviewRoundInline(admin.TabularInline):
    model = InterviewRound
    extra = 0
    readonly_fields = ('created_at',)


class ApplicationNoteInline(admin.TabularInline):
    model = ApplicationNote
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    """
    Admin configuration for the JobApplication model.
    """
    list_display = (
        'job_title',
        'company_name',
        'user',
        'status',
        'priority',
        'work_type',
        'applied_date',
        'updated_at',
    )
    list_filter = ('status', 'priority', 'work_type', 'created_at', 'applied_date')
    search_fields = ('job_title', 'company_name', 'user__username', 'user__email', 'location', 'source')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('status', 'priority')
    date_hierarchy = 'created_at'
    inlines = [InterviewRoundInline, ApplicationNoteInline]
    raw_id_fields = ('user', 'resume', 'cover_letter')

    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'job_title', 'company_name', 'job_url', 'job_description'),
        }),
        ('Status & Priority', {
            'fields': ('status', 'priority', 'work_type'),
        }),
        ('Compensation & Location', {
            'fields': ('salary_min', 'salary_max', 'location'),
        }),
        ('Documents', {
            'fields': ('resume', 'cover_letter'),
        }),
        ('Dates', {
            'fields': ('applied_date', 'response_date', 'created_at', 'updated_at'),
        }),
        ('Contact & Source', {
            'fields': ('contact_name', 'contact_email', 'source'),
        }),
        ('Notes', {
            'fields': ('notes',),
        }),
    )


@admin.register(InterviewRound)
class InterviewRoundAdmin(admin.ModelAdmin):
    """
    Admin configuration for the InterviewRound model.
    """
    list_display = (
        'application',
        'round_number',
        'type',
        'status',
        'scheduled_at',
        'interviewer',
        'created_at',
    )
    list_filter = ('type', 'status', 'scheduled_at')
    search_fields = (
        'application__job_title',
        'application__company_name',
        'interviewer',
    )
    readonly_fields = ('created_at',)
    raw_id_fields = ('application',)


@admin.register(ApplicationNote)
class ApplicationNoteAdmin(admin.ModelAdmin):
    """
    Admin configuration for the ApplicationNote model.
    """
    list_display = ('application', 'short_note', 'created_at')
    search_fields = ('application__job_title', 'application__company_name', 'note')
    readonly_fields = ('created_at',)
    raw_id_fields = ('application',)

    @admin.display(description='Note')
    def short_note(self, obj):
        """Return a truncated version of the note for list display."""
        return obj.note[:80] + '...' if len(obj.note) > 80 else obj.note
