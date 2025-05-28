from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Resume, ResumeVersion, ResumeSection
from .serializers import (
    ResumeSerializer, ResumeCreateSerializer, ResumeUpdateSerializer,
    ResumeDetailSerializer, ResumeVersionSerializer, ResumeSectionSerializer
)
from users.permissions import IsOwnerOrAdmin


class ResumeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Resume model.
    """
    queryset = Resume.objects.all()
    serializer_class = ResumeSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    
    def get_queryset(self):
        """
        Filter resumes based on user permissions.
        """
        if self.request.user.role == 'admin':
            return Resume.objects.all()
        return Resume.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        """
        Return appropriate serializer class based on the action.
        """
        if self.action == 'create':
            return ResumeCreateSerializer
        elif self.action == 'update' or self.action == 'partial_update':
            return ResumeUpdateSerializer
        elif self.action == 'retrieve':
            return ResumeDetailSerializer
        return ResumeSerializer
    
    def perform_create(self, serializer):
        """
        Set the user to the current user when creating a resume.
        """
        serializer.save()
    
    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """
        Get versions for a specific resume.
        """
        resume = self.get_object()
        versions = ResumeVersion.objects.filter(resume=resume)
        serializer = ResumeVersionSerializer(versions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def restore_version(self, request, pk=None):
        """
        Restore a specific version of a resume.
        """
        resume = self.get_object()
        version_id = request.query_params.get('version_id')
        
        if not version_id:
            return Response({"error": "Version ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            version = ResumeVersion.objects.get(id=version_id, resume=resume)
        except ResumeVersion.DoesNotExist:
            return Response({"error": "Version not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Update resume content with version content
        resume.content = version.content
        resume.save()
        
        # Create a new version
        latest_version = resume.versions.order_by('-version_number').first()
        version_number = latest_version.version_number + 1
        
        ResumeVersion.objects.create(
            resume=resume,
            content=version.content,
            version_number=version_number
        )
        
        serializer = ResumeDetailSerializer(resume)
        return Response(serializer.data)


class ResumeSectionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for ResumeSection model.
    """
    queryset = ResumeSection.objects.all()
    serializer_class = ResumeSectionSerializer
    permission_classes = [permissions.IsAuthenticated]