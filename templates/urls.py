from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TemplateCategoryViewSet, TemplateViewSet, TemplateSectionViewSet

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'categories', TemplateCategoryViewSet)
router.register(r'sections', TemplateSectionViewSet)
router.register(r'', TemplateViewSet)

# The API URLs are now determined automatically by the router
urlpatterns = [
    path('', include(router.urls)),
]