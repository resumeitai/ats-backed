from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from users.permissions import IsAdminUser
from analytics.services import AnalyticsService


class DashboardView(APIView):
    """
    GET: Return high-level dashboard statistics.
    Admin only.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        data = AnalyticsService.get_dashboard_stats()
        return Response(data, status=status.HTTP_200_OK)


class RevenueView(APIView):
    """
    GET: Return revenue analytics (MRR, total revenue, revenue by plan, avg transaction).
    Admin only.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        data = AnalyticsService.get_revenue_stats()
        return Response(data, status=status.HTTP_200_OK)


class UserActivityHeatmapView(APIView):
    """
    GET: Return user activity counts grouped by hour and day of week
    for rendering a heatmap on the admin dashboard.
    Admin only.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        data = AnalyticsService.get_user_activity_heatmap()
        return Response(data, status=status.HTTP_200_OK)


class TemplateUsageView(APIView):
    """
    GET: Return usage statistics for each template.
    Admin only.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        data = AnalyticsService.get_template_usage_stats()
        return Response(data, status=status.HTTP_200_OK)


class ATSStatsView(APIView):
    """
    GET: Return comprehensive ATS analytics (top job titles, score
    distribution, category averages, missing keywords).
    Admin only.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        data = AnalyticsService.get_ats_stats()
        return Response(data, status=status.HTTP_200_OK)


class OptimizationImpactView(APIView):
    """
    GET: Return optimization suggestion impact data.
    Admin only.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        data = AnalyticsService.get_optimization_impact()
        return Response(data, status=status.HTTP_200_OK)


class ExportCSVView(APIView):
    """
    GET: Export data as CSV.
    Query parameter ?type= must be one of: users, transactions, scores.
    Admin only.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        data_type = request.query_params.get('type')

        if data_type not in ('users', 'transactions', 'scores'):
            return Response(
                {'error': "Query parameter 'type' must be one of: users, transactions, scores."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            csv_content = AnalyticsService.export_csv(data_type)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="resumeit_{data_type}.csv"'
        return response
