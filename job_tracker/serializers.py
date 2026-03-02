from rest_framework import serializers
from .models import JobApplication, InterviewRound, ApplicationNote


class InterviewRoundSerializer(serializers.ModelSerializer):
    """
    Serializer for the InterviewRound model.
    """
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = InterviewRound
        fields = (
            'id',
            'application',
            'round_number',
            'type',
            'type_display',
            'scheduled_at',
            'duration_minutes',
            'interviewer',
            'notes',
            'feedback',
            'status',
            'status_display',
            'created_at',
        )
        read_only_fields = ('id', 'application', 'created_at')


class ApplicationNoteSerializer(serializers.ModelSerializer):
    """
    Serializer for the ApplicationNote model.
    """
    class Meta:
        model = ApplicationNote
        fields = ('id', 'application', 'note', 'created_at')
        read_only_fields = ('id', 'application', 'created_at')


class JobApplicationListSerializer(serializers.ModelSerializer):
    """
    Minimal serializer for job application list views.
    Returns only the essential fields needed for list/card display.
    """
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    work_type_display = serializers.CharField(source='get_work_type_display', read_only=True)
    interview_count = serializers.IntegerField(source='interview_rounds.count', read_only=True)

    class Meta:
        model = JobApplication
        fields = (
            'id',
            'job_title',
            'company_name',
            'location',
            'work_type',
            'work_type_display',
            'status',
            'status_display',
            'priority',
            'priority_display',
            'applied_date',
            'source',
            'interview_count',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class JobApplicationDetailSerializer(serializers.ModelSerializer):
    """
    Full serializer for job application detail views.
    Includes all fields plus nested interview rounds and activity notes.
    """
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    work_type_display = serializers.CharField(source='get_work_type_display', read_only=True)
    interview_rounds = InterviewRoundSerializer(many=True, read_only=True)
    activity_notes = ApplicationNoteSerializer(many=True, read_only=True)
    resume_title = serializers.CharField(source='resume.title', read_only=True, default=None)

    class Meta:
        model = JobApplication
        fields = (
            'id',
            'user',
            'resume',
            'resume_title',
            'cover_letter',
            'job_title',
            'company_name',
            'job_url',
            'job_description',
            'salary_min',
            'salary_max',
            'location',
            'work_type',
            'work_type_display',
            'status',
            'status_display',
            'priority',
            'priority_display',
            'applied_date',
            'response_date',
            'notes',
            'contact_name',
            'contact_email',
            'source',
            'interview_rounds',
            'activity_notes',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')


class JobApplicationCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating job applications.
    """
    class Meta:
        model = JobApplication
        fields = (
            'resume',
            'cover_letter',
            'job_title',
            'company_name',
            'job_url',
            'job_description',
            'salary_min',
            'salary_max',
            'location',
            'work_type',
            'status',
            'priority',
            'applied_date',
            'response_date',
            'notes',
            'contact_name',
            'contact_email',
            'source',
        )

    def validate(self, attrs):
        """
        Validate salary range: salary_min must not exceed salary_max.
        """
        salary_min = attrs.get('salary_min')
        salary_max = attrs.get('salary_max')
        if salary_min is not None and salary_max is not None and salary_min > salary_max:
            raise serializers.ValidationError({
                'salary_min': 'Minimum salary cannot exceed maximum salary.',
            })
        return attrs

    def validate_resume(self, value):
        """
        Ensure the resume belongs to the requesting user.
        """
        if value is not None:
            request = self.context.get('request')
            if request and value.user != request.user:
                raise serializers.ValidationError('You can only attach your own resumes.')
        return value

    def create(self, validated_data):
        user = self.context['request'].user
        return JobApplication.objects.create(user=user, **validated_data)


class KanbanColumnSerializer(serializers.Serializer):
    """
    Serializer for a single Kanban column (one status group).
    """
    status = serializers.CharField()
    status_display = serializers.CharField()
    count = serializers.IntegerField()
    applications = JobApplicationListSerializer(many=True)


class KanbanSerializer(serializers.Serializer):
    """
    Serializer that groups applications by status for Kanban board view.
    Returns a list of columns, each containing the status key, display name,
    count, and the list of applications in that column.
    """
    columns = KanbanColumnSerializer(many=True)
    total = serializers.IntegerField()
