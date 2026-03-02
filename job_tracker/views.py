from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Q, Avg, F
from django.utils import timezone

from .models import JobApplication, InterviewRound, ApplicationNote
from .serializers import (
    JobApplicationListSerializer,
    JobApplicationDetailSerializer,
    JobApplicationCreateUpdateSerializer,
    InterviewRoundSerializer,
    ApplicationNoteSerializer,
    KanbanSerializer,
)
from users.permissions import IsOwnerOrAdmin


class JobApplicationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing job applications with Kanban board support.

    Provides standard CRUD operations plus custom actions for:
    - Kanban board view (grouped by status)
    - Moving applications between status columns
    - Application statistics / analytics
    - Adding activity notes
    - Adding interview rounds
    """
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'updated_at', 'applied_date', 'company_name', 'job_title', 'priority']
    ordering = ['-updated_at']

    def get_queryset(self):
        """
        Return applications belonging to the current user.
        Admins can see all applications.
        Supports filtering via query params:
          ?status=applied
          ?priority=high
          ?company=Google
          ?work_type=remote
          ?source=LinkedIn
          ?search=python
        """
        if self.request.user.role == 'admin':
            queryset = JobApplication.objects.all()
        else:
            queryset = JobApplication.objects.filter(user=self.request.user)

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by priority
        priority_filter = self.request.query_params.get('priority')
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter)

        # Filter by company (case-insensitive contains)
        company_filter = self.request.query_params.get('company')
        if company_filter:
            queryset = queryset.filter(company_name__icontains=company_filter)

        # Filter by work type
        work_type_filter = self.request.query_params.get('work_type')
        if work_type_filter:
            queryset = queryset.filter(work_type=work_type_filter)

        # Filter by source
        source_filter = self.request.query_params.get('source')
        if source_filter:
            queryset = queryset.filter(source__icontains=source_filter)

        # Full-text search across job_title, company_name, job_description, notes
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(job_title__icontains=search)
                | Q(company_name__icontains=search)
                | Q(job_description__icontains=search)
                | Q(notes__icontains=search)
                | Q(location__icontains=search)
            )

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return JobApplicationListSerializer
        if self.action == 'retrieve':
            return JobApplicationDetailSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return JobApplicationCreateUpdateSerializer
        if self.action == 'kanban':
            return KanbanSerializer
        if self.action == 'add_note':
            return ApplicationNoteSerializer
        if self.action == 'add_interview':
            return InterviewRoundSerializer
        return JobApplicationListSerializer

    # ------------------------------------------------------------------
    # Custom actions
    # ------------------------------------------------------------------

    @action(detail=False, methods=['get'], url_path='kanban')
    def kanban(self, request):
        """
        Return all applications grouped by status for the Kanban board.
        Each column contains a list of applications serialized with the
        list serializer.
        """
        if request.user.role == 'admin':
            queryset = JobApplication.objects.all()
        else:
            queryset = JobApplication.objects.filter(user=request.user)

        # Preserve the defined column order from STATUS_CHOICES
        columns = []
        for status_key, status_label in JobApplication.STATUS_CHOICES:
            apps_in_column = queryset.filter(status=status_key).order_by('-updated_at')
            columns.append({
                'status': status_key,
                'status_display': status_label,
                'count': apps_in_column.count(),
                'applications': JobApplicationListSerializer(apps_in_column, many=True).data,
            })

        data = {
            'columns': columns,
            'total': queryset.count(),
        }
        return Response(data)

    @action(detail=True, methods=['post'], url_path='move')
    def move(self, request, pk=None):
        """
        Move an application to a new status (Kanban drag-and-drop).
        Expects: { "status": "interview" }
        Automatically sets applied_date when moving to 'applied' and
        response_date when moving to a response status.
        """
        application = self.get_object()
        new_status = request.data.get('status')

        if not new_status:
            return Response(
                {'error': 'The "status" field is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        valid_statuses = [choice[0] for choice in JobApplication.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return Response(
                {'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = application.status
        application.status = new_status

        # Auto-fill applied_date when first moving to 'applied'
        if new_status == 'applied' and application.applied_date is None:
            application.applied_date = timezone.now().date()

        # Auto-fill response_date on first response-type status change
        response_statuses = {'phone_screen', 'interview', 'technical', 'offer', 'accepted', 'rejected'}
        if new_status in response_statuses and application.response_date is None:
            application.response_date = timezone.now().date()

        application.save()

        # Create an activity note for the status change
        ApplicationNote.objects.create(
            application=application,
            note=f'Status changed from "{old_status}" to "{new_status}".',
        )

        serializer = JobApplicationDetailSerializer(application)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """
        Return aggregate statistics for the user's job applications.
        - total: total number of applications
        - by_status: count per status
        - by_priority: count per priority
        - response_rate: percentage of applications that received a response
        - avg_days_to_response: average calendar days between applied_date and response_date
        """
        if request.user.role == 'admin':
            queryset = JobApplication.objects.all()
        else:
            queryset = JobApplication.objects.filter(user=request.user)

        total = queryset.count()

        # Count by status
        by_status = {}
        status_counts = queryset.values('status').annotate(count=Count('id'))
        for entry in status_counts:
            by_status[entry['status']] = entry['count']

        # Ensure all statuses appear even if count is 0
        for status_key, _ in JobApplication.STATUS_CHOICES:
            by_status.setdefault(status_key, 0)

        # Count by priority
        by_priority = {}
        priority_counts = queryset.values('priority').annotate(count=Count('id'))
        for entry in priority_counts:
            by_priority[entry['priority']] = entry['count']
        for priority_key, _ in JobApplication.PRIORITY_CHOICES:
            by_priority.setdefault(priority_key, 0)

        # Response rate: applications that have a response_date out of those that have applied_date
        applied_qs = queryset.filter(applied_date__isnull=False)
        applied_count = applied_qs.count()
        responded_count = applied_qs.filter(response_date__isnull=False).count()
        response_rate = (
            round((responded_count / applied_count) * 100, 1)
            if applied_count > 0
            else 0.0
        )

        # Average days to response
        avg_days_to_response = (
            applied_qs.filter(response_date__isnull=False)
            .annotate(days=F('response_date') - F('applied_date'))
            .aggregate(avg_days=Avg('days'))
        )
        avg_days_val = avg_days_to_response.get('avg_days')
        if avg_days_val is not None:
            # avg_days_val is a timedelta when using date subtraction
            avg_days_result = round(avg_days_val.days if hasattr(avg_days_val, 'days') else float(avg_days_val), 1)
        else:
            avg_days_result = None

        # Count by work type
        by_work_type = {}
        work_type_counts = queryset.values('work_type').annotate(count=Count('id'))
        for entry in work_type_counts:
            by_work_type[entry['work_type']] = entry['count']
        for wt_key, _ in JobApplication.WORK_TYPE_CHOICES:
            by_work_type.setdefault(wt_key, 0)

        # Top sources
        top_sources = list(
            queryset.exclude(source='')
            .values('source')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        data = {
            'total': total,
            'by_status': by_status,
            'by_priority': by_priority,
            'by_work_type': by_work_type,
            'response_rate': response_rate,
            'avg_days_to_response': avg_days_result,
            'applied_count': applied_count,
            'responded_count': responded_count,
            'top_sources': top_sources,
        }
        return Response(data)

    @action(detail=True, methods=['post'], url_path='add-note')
    def add_note(self, request, pk=None):
        """
        Add an activity note to a job application.
        Expects: { "note": "Called the recruiter today." }
        """
        application = self.get_object()
        serializer = ApplicationNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(application=application)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='add-interview')
    def add_interview(self, request, pk=None):
        """
        Add an interview round to a job application.
        Expects fields from InterviewRoundSerializer (round_number, type, etc.).
        """
        application = self.get_object()
        serializer = InterviewRoundSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(application=application)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class InterviewRoundViewSet(viewsets.ModelViewSet):
    """
    Nested ViewSet for managing interview rounds under a job application.
    URL pattern: /applications/{application_pk}/interviews/
    """
    serializer_class = InterviewRoundSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        """
        Return interview rounds for the specified application,
        scoped to the current user.
        """
        application_pk = self.kwargs.get('application_pk')
        if self.request.user.role == 'admin':
            return InterviewRound.objects.filter(application_id=application_pk)
        return InterviewRound.objects.filter(
            application_id=application_pk,
            application__user=self.request.user,
        )

    def perform_create(self, serializer):
        """
        Save the interview round linked to the parent application.
        Validates that the application belongs to the current user.
        """
        application_pk = self.kwargs.get('application_pk')
        try:
            if self.request.user.role == 'admin':
                application = JobApplication.objects.get(pk=application_pk)
            else:
                application = JobApplication.objects.get(
                    pk=application_pk, user=self.request.user,
                )
        except JobApplication.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound('Job application not found.')

        serializer.save(application=application)
