from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, UserActivityViewSet, ReferralViewSet, RegisterView

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'', UserViewSet)
router.register(r'activities', UserActivityViewSet)
router.register(r'referrals', ReferralViewSet)

# The API URLs are now determined automatically by the router
urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('', include(router.urls)),
]