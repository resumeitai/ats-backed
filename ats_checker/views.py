from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import ATSScore, KeywordMatch, OptimizationSuggestion, JobTitleSynonym
from .serializers import (
    ATSScoreSerializer, ATSScoreCreateSerializer, KeywordMatchSerializer,
    OptimizationSuggestionSerializer, JobTitleSynonymSerializer, ApplySuggestionSerializer,
    ResumeOptimizeSerializer, OptimizedResumeSerializer,
)
from .services import apply_suggestion
from .optimizer import ResumeOptimizer
from .jd_parser import JobDescriptionParser
from .tasks import analyze_resume_task
from resumes.models import Resume, ResumeVersion
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
        """Create an ATS score and trigger async analysis."""
        ats_score = serializer.save()
        analyze_resume_task.delay(ats_score.id)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            {"message": "ATS analysis started. Results will be available shortly.", "id": serializer.instance.id},
            status=status.HTTP_202_ACCEPTED,
            headers=headers,
        )
    
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

    @action(detail=False, methods=['post'])
    def optimize_resume(self, request):
        """
        Optimize a resume for a specific job description.

        The user can paste a **raw job posting** (from LinkedIn, Indeed, etc.)
        as ``job_description``.  The endpoint automatically parses it to
        extract the relevant requirements and filters out noise (company
        description, benefits, legal disclaimers).

        ``job_title`` is optional — if omitted, the parser will auto-detect
        it from the raw text.

        If ``auto_apply`` is ``True``, the optimized content is saved back to
        the resume and a new ``ResumeVersion`` is created.
        """
        serializer = ResumeOptimizeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        resume = get_object_or_404(
            Resume,
            id=serializer.validated_data['resume_id'],
            user=request.user,
        )

        # Check premium subscription
        has_premium = request.user.subscriptions.filter(
            status='active', plan__is_premium=True
        ).exists()
        if not has_premium:
            return Response(
                {"error": "Resume Optimization is a premium feature. Please upgrade your subscription."},
                status=status.HTTP_403_FORBIDDEN,
            )

        raw_jd = serializer.validated_data['job_description']
        provided_title = serializer.validated_data.get('job_title', '')

        # Parse the raw job description to extract clean, relevant content
        parser = JobDescriptionParser(raw_jd)
        parsed = parser.parse()

        # Use provided title, or fall back to parser-detected title
        job_title = provided_title.strip() or parsed.get('job_title') or 'Software Developer'
        clean_description = parsed.get('clean_description') or raw_jd

        optimizer = ResumeOptimizer(
            resume_content=resume.content,
            job_title=job_title,
            job_description=clean_description,
        )
        result = optimizer.optimize()

        # Attach parsed JD metadata to the response
        result['parsed_job_info'] = {
            'detected_title': parsed.get('job_title'),
            'company': parsed.get('company_name'),
            'location': parsed.get('location'),
            'experience_level': parsed.get('experience_level'),
            'skills_found': parsed.get('skills_mentioned', []),
            'requirements_count': len(parsed.get('requirements', [])),
            'responsibilities_count': len(parsed.get('responsibilities', [])),
        }

        # If auto_apply is True, persist the optimized content
        if serializer.validated_data.get('auto_apply'):
            resume.content = result['optimized_content']
            resume.save()

            # Create a new ResumeVersion
            latest = resume.versions.order_by('-version_number').first()
            version_num = (latest.version_number + 1) if latest else 1
            ResumeVersion.objects.create(
                resume=resume,
                content=result['optimized_content'],
                version_number=version_num,
            )

        return Response(OptimizedResumeSerializer(result).data)

    @action(detail=False, methods=['get'])
    def supported_languages(self, request):
        """Return list of supported languages for multi-language ATS analysis."""
        from .nlp.multilang import get_supported_languages
        return Response(get_supported_languages())

    @action(detail=False, methods=['post'])
    def detect_language(self, request):
        """Detect language of the provided text."""
        from .nlp.multilang import detect_language as detect_lang
        text = request.data.get('text', '')
        if not text:
            return Response({"error": "text field is required."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"language": detect_lang(text)})


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