from django.urls import path

from analytics.views import (
    DashboardView,
    RevenueView,
    UserActivityHeatmapView,
    TemplateUsageView,
    ATSStatsView,
    OptimizationImpactView,
    ExportCSVView,
)

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('revenue/', RevenueView.as_view(), name='revenue'),
    path('user-activity-heatmap/', UserActivityHeatmapView.as_view(), name='user-activity-heatmap'),
    path('template-usage/', TemplateUsageView.as_view(), name='template-usage'),
    path('ats/', ATSStatsView.as_view(), name='ats-stats'),
    path('optimization-impact/', OptimizationImpactView.as_view(), name='optimization-impact'),
    path('export/', ExportCSVView.as_view(), name='export-csv'),
]
