import logging

from django.http import HttpResponse
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from resumes.models import Resume
from users.permissions import IsOwnerOrAdmin

from .models import CoverLetter
from .serializers import (
    CoverLetterSerializer,
    CoverLetterGenerateSerializer,
    CoverLetterEditSerializer,
)
from .services import CoverLetterGenerator

logger = logging.getLogger(__name__)


class CoverLetterViewSet(viewsets.ModelViewSet):
    """
    ViewSet for the CoverLetter model.

    Provides standard CRUD operations plus custom actions for
    regenerating a cover letter and exporting it as plain text.

    Endpoints:
        GET    /cover-letters/             - list user's cover letters
        POST   /cover-letters/             - generate a new cover letter
        GET    /cover-letters/{id}/        - retrieve a single cover letter
        PUT    /cover-letters/{id}/        - full update (manual edit)
        PATCH  /cover-letters/{id}/        - partial update (manual edit)
        DELETE /cover-letters/{id}/        - delete a cover letter
        POST   /cover-letters/{id}/regenerate/   - regenerate content
        GET    /cover-letters/{id}/export_text/  - download as .txt
    """

    queryset = CoverLetter.objects.all()
    serializer_class = CoverLetterSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    # ------------------------------------------------------------------
    # Queryset filtering
    # ------------------------------------------------------------------

    def get_queryset(self):
        """
        Filter cover letters by the current user.
        Admin users can see all cover letters.
        """
        if self.request.user.role == 'admin':
            return CoverLetter.objects.all()
        return CoverLetter.objects.filter(user=self.request.user)

    # ------------------------------------------------------------------
    # Serializer selection
    # ------------------------------------------------------------------

    def get_serializer_class(self):
        if self.action == 'create':
            return CoverLetterGenerateSerializer
        if self.action in ('update', 'partial_update'):
            return CoverLetterEditSerializer
        return CoverLetterSerializer

    # ------------------------------------------------------------------
    # Create (generate)
    # ------------------------------------------------------------------

    def create(self, request, *args, **kwargs):
        """
        Generate a new cover letter.

        Accepts a resume ID, job title, job description, and optional
        company name and tone. The NLP-based generator produces the
        cover letter content locally.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        resume_id = data['resume_id']
        job_title = data['job_title']
        job_description = data['job_description']
        company_name = data.get('company_name', '')
        tone = data.get('tone', 'professional')

        # Fetch the resume (already validated by the serializer)
        resume = Resume.objects.get(pk=resume_id, is_deleted=False)

        # Generate the cover letter content
        try:
            generator = CoverLetterGenerator(
                resume=resume,
                job_title=job_title,
                job_description=job_description,
                company_name=company_name,
                tone=tone,
            )
            content = generator.generate()
        except Exception as e:
            logger.exception("Cover letter generation failed: %s", e)
            return Response(
                {"error": "Cover letter generation failed. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Persist the cover letter
        cover_letter = CoverLetter.objects.create(
            user=request.user,
            resume=resume,
            job_title=job_title,
            company_name=company_name,
            job_description=job_description,
            content=content,
            tone=tone,
        )

        # Return the full representation
        output_serializer = CoverLetterSerializer(cover_letter)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    # ------------------------------------------------------------------
    # Custom actions
    # ------------------------------------------------------------------

    @action(detail=True, methods=['post'])
    def regenerate(self, request, pk=None):
        """
        Regenerate the cover letter content for an existing record.

        Optionally accepts ``tone`` in the request body to change the
        tone on regeneration.
        """
        cover_letter = self.get_object()

        # Allow tone override
        new_tone = request.data.get('tone', cover_letter.tone)
        if new_tone not in dict(CoverLetter.TONE_CHOICES):
            new_tone = cover_letter.tone

        # The resume may have been deleted; handle gracefully
        resume = cover_letter.resume
        if resume is None:
            return Response(
                {"error": "The associated resume has been deleted. Cannot regenerate."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            generator = CoverLetterGenerator(
                resume=resume,
                job_title=cover_letter.job_title,
                job_description=cover_letter.job_description,
                company_name=cover_letter.company_name,
                tone=new_tone,
            )
            content = generator.generate()
        except Exception as e:
            logger.exception("Cover letter regeneration failed: %s", e)
            return Response(
                {"error": "Cover letter regeneration failed. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        cover_letter.content = content
        cover_letter.tone = new_tone
        cover_letter.is_edited = False
        cover_letter.save(update_fields=['content', 'tone', 'is_edited', 'updated_at'])

        serializer = CoverLetterSerializer(cover_letter)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def export_text(self, request, pk=None):
        """
        Export the cover letter as a plain text file download.
        """
        cover_letter = self.get_object()

        # Build a filename from job title and company
        safe_title = "".join(
            c if c.isalnum() or c in (' ', '-', '_') else ''
            for c in cover_letter.job_title
        ).strip().replace(' ', '_')
        safe_company = "".join(
            c if c.isalnum() or c in (' ', '-', '_') else ''
            for c in cover_letter.company_name
        ).strip().replace(' ', '_')

        if safe_company:
            filename = f"Cover_Letter_{safe_title}_{safe_company}.txt"
        else:
            filename = f"Cover_Letter_{safe_title}.txt"

        response = HttpResponse(cover_letter.content, content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
