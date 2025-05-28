from rest_framework import serializers
from .models import Resume, ResumeVersion, ResumeSection
from users.serializers import UserSerializer


class ResumeSectionSerializer(serializers.ModelSerializer):
    """
    Serializer for the ResumeSection model.
    """
    class Meta:
        model = ResumeSection
        fields = ('id', 'name', 'type', 'is_required', 'order')


class ResumeVersionSerializer(serializers.ModelSerializer):
    """
    Serializer for the ResumeVersion model.
    """
    class Meta:
        model = ResumeVersion
        fields = ('id', 'resume', 'content', 'version_number', 'created_at')
        read_only_fields = ('id', 'created_at')


class ResumeSerializer(serializers.ModelSerializer):
    """
    Serializer for the Resume model.
    """
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Resume
        fields = ('id', 'user', 'template', 'title', 'content', 'is_active', 'created_at', 'updated_at')
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')


class ResumeCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a resume.
    """
    class Meta:
        model = Resume
        fields = ('template', 'title', 'content', 'is_active')
    
    def create(self, validated_data):
        user = self.context['request'].user
        resume = Resume.objects.create(user=user, **validated_data)
        
        # Create initial version
        ResumeVersion.objects.create(
            resume=resume,
            content=validated_data.get('content', {}),
            version_number=1
        )
        
        return resume


class ResumeUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating a resume.
    """
    class Meta:
        model = Resume
        fields = ('template', 'title', 'content', 'is_active')
    
    def update(self, instance, validated_data):
        # Update the resume
        instance = super().update(instance, validated_data)
        
        # Create a new version if content has changed
        if 'content' in validated_data:
            # Get the latest version number
            latest_version = instance.versions.order_by('-version_number').first()
            version_number = 1 if not latest_version else latest_version.version_number + 1
            
            # Create new version
            ResumeVersion.objects.create(
                resume=instance,
                content=validated_data['content'],
                version_number=version_number
            )
        
        return instance


class ResumeDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for detailed resume view.
    """
    user = UserSerializer(read_only=True)
    versions = ResumeVersionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Resume
        fields = ('id', 'user', 'template', 'title', 'content', 'is_active', 'created_at', 'updated_at', 'versions')
        read_only_fields = ('id', 'user', 'created_at', 'updated_at', 'versions')