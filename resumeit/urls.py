"""
URL configuration for resumeit project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from rest_framework.throttling import ScopedRateThrottle
from django.http import JsonResponse


class ThrottledTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'


class ThrottledTokenRefreshView(TokenRefreshView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'


def home_view(request):
    return JsonResponse({
        "message": "Welcome to the ResumeIt API",
        "version": "1.0.0",
        "routes": {
            "admin": "/admin/",
            "docs": "/swagger/",
            "health": "/api/v1/health/",
            "token": "/api/v1/token/",
            "users": "/api/v1/users/",
            "resumes": "/api/v1/resumes/",
            "templates": "/api/v1/templates/",
            "subscriptions": "/api/v1/subscriptions/",
            "ats": "/api/v1/ats/",
            "notifications": "/api/v1/notifications/",
            "analytics": "/api/v1/analytics/",
            "job_tracker": "/api/v1/job-tracker/",
            "cover_letters": "/api/v1/cover-letters/",
        }
    })


def health_check(request):
    return JsonResponse({"status": "healthy", "version": "1.0.0"})


# Schema view for API documentation
schema_view = get_schema_view(
    openapi.Info(
        title="ResumeIt ATS API",
        default_version='v1',
        description="API for Applicant Tracking System with resume parsing and ranking capabilities",
        terms_of_service="https://www.example.com/terms/",
        contact=openapi.Contact(email="contact@example.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

# Versioned API routes
api_v1_patterns = [
    path('token/', ThrottledTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', ThrottledTokenRefreshView.as_view(), name='token_refresh'),
    path('health/', health_check, name='health-check'),
    path('users/', include('users.urls')),
    path('resumes/', include('resumes.urls')),
    path('templates/', include('templates.urls')),
    path('subscriptions/', include('subscriptions.urls')),
    path('ats/', include('ats_checker.urls')),
    path('notifications/', include('notifications.urls')),
    path('analytics/', include('analytics.urls')),
    path('job-tracker/', include('job_tracker.urls')),
    path('cover-letters/', include('cover_letters.urls')),
]

urlpatterns = [
    path('', home_view),
    path('admin/', admin.site.urls),

    # API documentation
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    # Versioned API
    path('api/v1/', include(api_v1_patterns)),

    # Backward-compatible unversioned routes (redirect to v1)
    path('api/token/', ThrottledTokenObtainPairView.as_view()),
    path('api/token/refresh/', ThrottledTokenRefreshView.as_view()),
    path('api/users/', include('users.urls')),
    path('api/resumes/', include('resumes.urls')),
    path('api/templates/', include('templates.urls')),
    path('api/subscriptions/', include('subscriptions.urls')),
    path('api/ats/', include('ats_checker.urls')),
    path('api/notifications/', include('notifications.urls')),
    path('api/analytics/', include('analytics.urls')),
    path('api/job-tracker/', include('job_tracker.urls')),
    path('api/cover-letters/', include('cover_letters.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
