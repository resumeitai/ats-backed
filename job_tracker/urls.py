from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import JobApplicationViewSet, InterviewRoundViewSet

router = DefaultRouter()
router.register(r'', JobApplicationViewSet, basename='jobapplication')

# Nested router for interview rounds under a specific application
interview_router = DefaultRouter()
interview_router.register(r'', InterviewRoundViewSet, basename='interviewround')

urlpatterns = [
    path('', include(router.urls)),
    path(
        '<int:application_pk>/interviews/',
        include(interview_router.urls),
    ),
]
