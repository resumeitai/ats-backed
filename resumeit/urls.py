"""
URL configuration for ats_backend project.
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
from django.http import JsonResponse

def home_view(request):
    return JsonResponse({
        "message": "Welcome to the ResumeIt API",
        "routes": [
            "admin/",
            "swagger/ [name='schema-swagger-ui']",
            "redoc/ [name='schema-redoc']",
            "api/token/ [name='token_obtain_pair']",
            "api/token/refresh/ [name='token_refresh']",
            "api/users/",
            "api/resumes/",
            "api/templates/",
            "api/subscriptions/",
            "api/ats/",
            "media/<path>",
        ]
    })

# Schema view for API documentation
schema_view = get_schema_view(
    openapi.Info(
        title="ATS Resume Ranking API",
        default_version='v1',
        description="API for Applicant Tracking System with resume parsing and ranking capabilities",
        terms_of_service="https://www.example.com/terms/",
        contact=openapi.Contact(email="contact@example.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # Admin site
    path('', home_view),  # Add this line for the root endpoint
    path('admin/', admin.site.urls),
    
    # API documentation
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
   # JWT Authentication
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # API endpoints
    path('api/users/', include('users.urls')),
    path('api/resumes/', include('resumes.urls')),
    path('api/templates/', include('templates.urls')),
    path('api/subscriptions/', include('subscriptions.urls')),
    path('api/ats/', include('ats_checker.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)