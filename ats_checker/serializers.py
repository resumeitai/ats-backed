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
