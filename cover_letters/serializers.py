from rest_framework import serializers
from .models import CoverLetter
from resumes.models import Resume


class CoverLetterSerializer(serializers.ModelSerializer):
    """
    Read serializer for the CoverLetter model.

    Returns all fields including the generated content and metadata.
    """
    user_username = serializers.CharField(source='user.username', read_only=True)
    resume_title = serializers.CharField(source='resume.title', read_only=True, default=None)

    class Meta:
        model = CoverLetter
        fields = (
            'id',
            'user',
            'user_username',
            'resume',
            'resume_title',
            'job_title',
            'company_name',
            'job_description',
            'content',
            'tone',
            'is_edited',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'user',
            'user_username',
            'resume_title',
            'content',
            'is_edited',
            'created_at',
            'updated_at',
        )


class CoverLetterGenerateSerializer(serializers.Serializer):
    """
    Serializer for creating / generating a cover letter.

    Accepts a resume ID, job title, job description, and optional
    company name and tone. Validates that the resume belongs to the
    requesting user.
    """
    resume_id = serializers.IntegerField()
    job_title = serializers.CharField(max_length=255)
    job_description = serializers.CharField()
    company_name = serializers.CharField(max_length=255, required=False, default='')
    tone = serializers.ChoiceField(
        choices=CoverLetter.TONE_CHOICES,
        required=False,
        default='professional',
    )

    def validate_resume_id(self, value):
        """Ensure the resume exists and belongs to the current user."""
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError("Authentication required.")

        try:
            resume = Resume.objects.get(pk=value, is_deleted=False)
        except Resume.DoesNotExist:
            raise serializers.ValidationError("Resume not found.")

        # Only the resume owner (or an admin) may use this resume
        if resume.user != request.user and request.user.role != 'admin':
            raise serializers.ValidationError("You do not have permission to use this resume.")

        return value

    def validate_job_description(self, value):
        """Ensure the job description has enough content for meaningful analysis."""
        if len(value.strip()) < 20:
            raise serializers.ValidationError(
                "Job description is too short. Please provide a more detailed description."
            )
        return value


class CoverLetterEditSerializer(serializers.ModelSerializer):
    """
    Serializer for manual edits to the cover letter content.

    Only the ``content`` field is writable. Saving automatically sets
    ``is_edited`` to ``True``.
    """

    class Meta:
        model = CoverLetter
        fields = ('id', 'content', 'is_edited', 'updated_at')
        read_only_fields = ('id', 'is_edited', 'updated_at')

    def update(self, instance, validated_data):
        instance.content = validated_data.get('content', instance.content)
        instance.is_edited = True
        instance.save(update_fields=['content', 'is_edited', 'updated_at'])
        return instance
