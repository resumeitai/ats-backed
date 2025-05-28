from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ATSScoreViewSet, JobTitleSynonymViewSet

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'scores', ATSScoreViewSet)
router.register(r'job-title-synonyms', JobTitleSynonymViewSet)

# The API URLs are now determined automatically by the router
urlpatterns = [
    path('', include(router.urls)),
]