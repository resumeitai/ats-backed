from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CoverLetterViewSet

router = DefaultRouter()
router.register(r'', CoverLetterViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
