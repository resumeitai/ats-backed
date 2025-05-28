from rest_framework import serializers
from .models import TemplateCategory, Template, TemplateSection


class TemplateSectionSerializer(serializers.ModelSerializer):
    """
    Serializer for the TemplateSection model.
    """
    class Meta:
        model = TemplateSection
        fields = ('id', 'name', 'html_id', 'order', 'is_required')


class TemplateCategorySerializer(serializers.ModelSerializer):
    """
    Serializer for the TemplateCategory model.
    """
    class Meta:
        model = TemplateCategory
        fields = ('id', 'name', 'description')


class TemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for the Template model.
    """
    category = TemplateCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=TemplateCategory.objects.all(),
        source='category',
        write_only=True
    )
    
    class Meta:
        model = Template
        fields = ('id', 'name', 'description', 'category', 'category_id', 'thumbnail', 
                  'is_premium', 'is_active', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class TemplateDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for detailed template view.
    """
    category = TemplateCategorySerializer(read_only=True)
    sections = TemplateSectionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Template
        fields = ('id', 'name', 'description', 'category', 'thumbnail', 'html_structure', 
                  'css_styles', 'is_premium', 'is_active', 'created_at', 'updated_at', 'sections')
        read_only_fields = ('id', 'created_at', 'updated_at')


class TemplateCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating templates.
    """
    sections = TemplateSectionSerializer(many=True, required=False)
    
    class Meta:
        model = Template
        fields = ('name', 'description', 'category', 'thumbnail', 'html_structure', 
                  'css_styles', 'is_premium', 'is_active', 'sections')
    
    def create(self, validated_data):
        sections_data = validated_data.pop('sections', [])
        template = Template.objects.create(**validated_data)
        
        for section_data in sections_data:
            TemplateSection.objects.create(template=template, **section_data)
        
        return template
    
    def update(self, instance, validated_data):
        sections_data = validated_data.pop('sections', [])
        
        # Update template fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update sections if provided
        if sections_data:
            # Remove existing sections
            instance.sections.all().delete()
            
            # Create new sections
            for section_data in sections_data:
                TemplateSection.objects.create(template=instance, **section_data)
        
        return instance