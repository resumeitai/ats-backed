from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import TemplateCategory, Template, TemplateSection
from .serializers import (
    TemplateCategorySerializer, TemplateSerializer, TemplateDetailSerializer,
    TemplateCreateUpdateSerializer, TemplateSectionSerializer
)
from users.permissions import IsAdminUser


class TemplateCategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for TemplateCategory model.
    """
    queryset = TemplateCategory.objects.all()
    serializer_class = TemplateCategorySerializer
    
    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]


class TemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Template model.
    """
    queryset = Template.objects.filter(is_active=True)
    serializer_class = TemplateSerializer
    
    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        """
        Return appropriate serializer class based on the action.
        """
        if self.action == 'retrieve':
            return TemplateDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return TemplateCreateUpdateSerializer
        return TemplateSerializer
    
    def get_queryset(self):
        """
        Filter templates based on query parameters.
        """
        queryset = Template.objects.filter(is_active=True)
        
        # Filter by category
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Filter by premium status
        is_premium = self.request.query_params.get('is_premium')
        if is_premium is not None:
            is_premium = is_premium.lower() == 'true'
            queryset = queryset.filter(is_premium=is_premium)
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def sections(self, request, pk=None):
        """
        Get sections for a specific template.
        """
        template = self.get_object()
        sections = TemplateSection.objects.filter(template=template)
        serializer = TemplateSectionSerializer(sections, many=True)
        return Response(serializer.data)


class TemplateSectionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for TemplateSection model.
    """
    queryset = TemplateSection.objects.all()
    serializer_class = TemplateSectionSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        """
        Filter sections based on template.
        """
        queryset = TemplateSection.objects.all()
        
        # Filter by template
        template_id = self.request.query_params.get('template')
        if template_id:
            queryset = queryset.filter(template_id=template_id)
        
        return queryset