from rest_framework import serializers
from .models import ATSScore, KeywordMatch, OptimizationSuggestion, JobTitleSynonym
from users.serializers import UserSerializer
from resumes.serializers import ResumeSerializer
from resumes.models import Resume


class KeywordMatchSerializer(serializers.ModelSerializer):
    """
    Serializer for the KeywordMatch model.
    """
    class Meta:
        model = KeywordMatch
        fields = ('id', 'keyword', 'found', 'importance', 'context')
        read_only_fields = ('id',)


class OptimizationSuggestionSerializer(serializers.ModelSerializer):
    """
    Serializer for the OptimizationSuggestion model.
    """
    class Meta:
        model = OptimizationSuggestion
        fields = ('id', 'section', 'original_text', 'suggested_text', 'reason', 'applied')
        read_only_fields = ('id',)


class ATSScoreSerializer(serializers.ModelSerializer):
    """
    Serializer for the ATSScore model.
    """
    user = UserSerializer(read_only=True)
    resume = ResumeSerializer(read_only=True)
    keyword_matches = KeywordMatchSerializer(many=True, read_only=True)
    optimization_suggestions = OptimizationSuggestionSerializer(many=True, read_only=True)

    class Meta:
        model = ATSScore
        fields = ('id', 'user', 'resume', 'job_title', 'job_description', 'score', 
                  'analysis', 'suggestions', 'keyword_matches', 'optimization_suggestions', 
                  'created_at', 'updated_at')
        read_only_fields = ('id', 'user', 'score', 'analysis', 'suggestions', 'created_at', 'updated_at')


class ATSScoreCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating an ATS score.
    """
    resume_id = serializers.PrimaryKeyRelatedField(
        source='resume',
        queryset=Resume.objects.all()
    )

    class Meta:
        model = ATSScore
        fields = ('resume_id', 'job_title', 'job_description')

    def create(self, validated_data):
        user = self.context['request'].user

        # Check if user has premium subscription
        has_premium = user.subscriptions.filter(status='active', plan__is_premium=True).exists()
        if not has_premium:
            raise serializers.ValidationError({"error": "ATS Score Checker is a premium feature. Please upgrade your subscription."})

        # Create ATS score (actual scoring will be done in the view)
        ats_score = ATSScore.objects.create(
            user=user,
            **validated_data
        )

        return ats_score


class JobTitleSynonymSerializer(serializers.ModelSerializer):
    """
    Serializer for the JobTitleSynonym model.
    """
    class Meta:
        model = JobTitleSynonym
        fields = ('id', 'title', 'synonyms')
        read_only_fields = ('id',)


class ApplySuggestionSerializer(serializers.Serializer):
    """
    Serializer for applying optimization suggestions.
    """
    suggestion_id = serializers.IntegerField()

    def validate_suggestion_id(self, value):
        try:
            suggestion = OptimizationSuggestion.objects.get(id=value)
            if suggestion.applied:
                raise serializers.ValidationError("This suggestion has already been applied.")
            return value
        except OptimizationSuggestion.DoesNotExist:
            raise serializers.ValidationError("Suggestion not found.")


class ResumeOptimizeSerializer(serializers.Serializer):
    """
    Serializer for the resume optimization request.

    The user can paste a full raw job posting (from LinkedIn, Indeed, etc.)
    as ``job_description``.  ``job_title`` is optional — if omitted, the
    parser will attempt to extract it from the raw text.
    """
    resume_id = serializers.IntegerField()
    job_title = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    job_description = serializers.CharField()
    auto_apply = serializers.BooleanField(default=False)

    def validate_resume_id(self, value):
        try:
            Resume.objects.get(id=value)
        except Resume.DoesNotExist:
            raise serializers.ValidationError("Resume not found.")
        return value


class OptimizationChangeSerializer(serializers.Serializer):
    """
    Serializer for a single change entry in the optimization report.
    """
    section = serializers.CharField()
    original = serializers.CharField()
    modified = serializers.CharField()
    reason = serializers.CharField()


class ParsedJobInfoSerializer(serializers.Serializer):
    """Metadata extracted from the raw job posting by the JD parser."""
    detected_title = serializers.CharField(allow_null=True)
    company = serializers.CharField(allow_null=True)
    location = serializers.CharField(allow_null=True)
    experience_level = serializers.CharField(allow_null=True)
    skills_found = serializers.ListField(child=serializers.CharField())
    requirements_count = serializers.IntegerField()
    responsibilities_count = serializers.IntegerField()


class OptimizedResumeSerializer(serializers.Serializer):
    """
    Serializer for the optimization result returned by ResumeOptimizer.
    """
    optimized_content = serializers.JSONField()
    original_content = serializers.JSONField()
    changes = OptimizationChangeSerializer(many=True)
    score_before = serializers.IntegerField()
    score_after = serializers.IntegerField()
    improvement = serializers.IntegerField()
    parsed_job_info = ParsedJobInfoSerializer(required=False)
