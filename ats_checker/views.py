from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import ATSScore, KeywordMatch, OptimizationSuggestion, JobTitleSynonym
from .serializers import (
    ATSScoreSerializer, ATSScoreCreateSerializer, KeywordMatchSerializer,
    OptimizationSuggestionSerializer, JobTitleSynonymSerializer, ApplySuggestionSerializer
)
from .services import analyze_resume, apply_suggestion
from users.permissions import IsAdminUser, IsOwnerOrAdmin


class ATSScoreViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ATSScore model.
    """
    queryset = ATSScore.objects.all()
    serializer_class = ATSScoreSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    
    def get_queryset(self):
        """
        Filter ATS scores based on user permissions.
        """
        if self.request.user.role == 'admin':
            return ATSScore.objects.all()
        return ATSScore.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        """
        Return appropriate serializer class based on the action.
        """
        if self.action == 'create':
            return ATSScoreCreateSerializer
        return ATSScoreSerializer
    
    def perform_create(self, serializer):
        """
        Create an ATS score and analyze the resume.
        """
        # Save the ATS score
        ats_score = serializer.save()
        
        # Analyze the resume (in a real app, this would be done asynchronously with Celery)
        analyze_resume(ats_score.id)
    
    @action(detail=True, methods=['post'])
    def apply_suggestion(self, request, pk=None):
        """
        Apply a suggestion to a resume.
        """
        ats_score = self.get_object()
        serializer = ApplySuggestionSerializer(data=request.data)
        
        if serializer.is_valid():
            suggestion_id = serializer.validated_data['suggestion_id']
            
            # Check if the suggestion belongs to this ATS score
            suggestion = get_object_or_404(OptimizationSuggestion, id=suggestion_id, ats_score=ats_score)
            
            # Apply the suggestion
            success = apply_suggestion(suggestion_id)
            
            if success:
                return Response({"message": "Suggestion applied successfully"})
            else:
                return Response({"error": "Failed to apply suggestion"}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def keyword_matches(self, request, pk=None):
        """
        Get keyword matches for a specific ATS score.
        """
        ats_score = self.get_object()
        keyword_matches = KeywordMatch.objects.filter(ats_score=ats_score)
        serializer = KeywordMatchSerializer(keyword_matches, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def optimization_suggestions(self, request, pk=None):
        """
        Get optimization suggestions for a specific ATS score.
        """
        ats_score = self.get_object()
        suggestions = OptimizationSuggestion.objects.filter(ats_score=ats_score)
        serializer = OptimizationSuggestionSerializer(suggestions, many=True)
        return Response(serializer.data)


class JobTitleSynonymViewSet(viewsets.ModelViewSet):
    """
    ViewSet for JobTitleSynonym model.
    """
    queryset = JobTitleSynonym.objects.all()
    serializer_class = JobTitleSynonymSerializer
    
    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]