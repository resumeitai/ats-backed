from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
from django.utils import timezone
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
        Filter resumes based on user permissions. Excludes soft-deleted.
        """
        if getattr(self, 'swagger_fake_view', False):
            return Resume.objects.none()
        if self.request.user.role == 'admin':
            return Resume.objects.filter(is_deleted=False)
        return Resume.objects.filter(user=self.request.user, is_deleted=False)

    def get_serializer_class(self):
        if self.action == 'create':
            return ResumeCreateSerializer
        elif self.action in ('update', 'partial_update'):
            return ResumeUpdateSerializer
        elif self.action == 'retrieve':
            return ResumeDetailSerializer
        return ResumeSerializer

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        resume = self.get_object()
        versions = ResumeVersion.objects.filter(resume=resume)
        serializer = ResumeVersionSerializer(versions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def restore_version(self, request, pk=None):
        resume = self.get_object()
        version_id = request.query_params.get('version_id')

        if not version_id:
            return Response({"error": "Version ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            version = ResumeVersion.objects.get(id=version_id, resume=resume)
        except ResumeVersion.DoesNotExist:
            return Response({"error": "Version not found"}, status=status.HTTP_404_NOT_FOUND)

        resume.content = version.content
        resume.save()

        latest_version = resume.versions.order_by('-version_number').first()
        version_number = latest_version.version_number + 1

        ResumeVersion.objects.create(
            resume=resume,
            content=version.content,
            version_number=version_number
        )

        serializer = ResumeDetailSerializer(resume)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def soft_delete(self, request, pk=None):
        """Soft delete a resume."""
        resume = self.get_object()
        resume.is_deleted = True
        resume.deleted_at = timezone.now()
        resume.save(update_fields=['is_deleted', 'deleted_at'])
        return Response({"message": "Resume deleted successfully."})

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Restore a soft-deleted resume."""
        try:
            if request.user.role == 'admin':
                resume = Resume.objects.get(pk=pk, is_deleted=True)
            else:
                resume = Resume.objects.get(pk=pk, user=request.user, is_deleted=True)
        except Resume.DoesNotExist:
            return Response({"error": "Deleted resume not found."}, status=status.HTTP_404_NOT_FOUND)

        resume.is_deleted = False
        resume.deleted_at = None
        resume.save(update_fields=['is_deleted', 'deleted_at'])
        return Response({"message": "Resume restored successfully."})

    @action(detail=True, methods=['get'])
    def export_pdf(self, request, pk=None):
        """Export resume as PDF."""
        resume = self.get_object()
        try:
            from .export_service import ResumeExporter
            exporter = ResumeExporter(resume)
            pdf_bytes = exporter.export_pdf()
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{resume.title}.pdf"'
            return response
        except ImportError:
            return Response(
                {"error": "PDF export dependencies not installed. Install xhtml2pdf."},
                status=status.HTTP_501_NOT_IMPLEMENTED
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def export_docx(self, request, pk=None):
        """Export resume as DOCX."""
        resume = self.get_object()
        try:
            from .export_service import ResumeExporter
            exporter = ResumeExporter(resume)
            docx_bytes = exporter.export_docx()
            response = HttpResponse(
                docx_bytes,
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            response['Content-Disposition'] = f'attachment; filename="{resume.title}.docx"'
            return response
        except ImportError:
            return Response(
                {"error": "DOCX export dependencies not installed. Install python-docx."},
                status=status.HTTP_501_NOT_IMPLEMENTED
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def compare(self, request, pk=None):
        """
        Compare two resume versions side-by-side.
        Query params: version_a (required), version_b (optional, defaults to current content).
        """
        resume = self.get_object()
        version_a_id = request.query_params.get('version_a')
        version_b_id = request.query_params.get('version_b')

        if not version_a_id:
            return Response(
                {"error": "version_a query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            version_a = ResumeVersion.objects.get(id=version_a_id, resume=resume)
        except ResumeVersion.DoesNotExist:
            return Response({"error": "Version A not found."}, status=status.HTTP_404_NOT_FOUND)

        if version_b_id:
            try:
                version_b = ResumeVersion.objects.get(id=version_b_id, resume=resume)
            except ResumeVersion.DoesNotExist:
                return Response({"error": "Version B not found."}, status=status.HTTP_404_NOT_FOUND)
            content_b = version_b.content
            label_b = f"Version {version_b.version_number}"
        else:
            content_b = resume.content
            label_b = "Current"

        from .comparison_service import ResumeComparator
        comparator = ResumeComparator(
            content_a=version_a.content,
            content_b=content_b,
            label_a=f"Version {version_a.version_number}",
            label_b=label_b,
        )
        return Response(comparator.compare())

    @action(detail=False, methods=['post'])
    def import_linkedin(self, request):
        """
        Import resume data from LinkedIn profile JSON.
        Accepts: {"linkedin_data": {<linkedin profile JSON>}}
        """
        from .linkedin_import import LinkedInImporter

        linkedin_data = request.data.get('linkedin_data')
        if not linkedin_data:
            return Response(
                {"error": "linkedin_data JSON is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            importer = LinkedInImporter(linkedin_data)
            resume_content = importer.parse()

            resume = Resume.objects.create(
                user=request.user,
                title=f"LinkedIn Import - {resume_content.get('personal', {}).get('name', 'Untitled')}",
                content=resume_content,
            )
            ResumeVersion.objects.create(
                resume=resume,
                content=resume_content,
                version_number=1,
            )

            serializer = ResumeDetailSerializer(resume)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ResumeSectionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for ResumeSection model.
    """
    queryset = ResumeSection.objects.all()
    serializer_class = ResumeSectionSerializer
    permission_classes = [permissions.IsAuthenticated]
