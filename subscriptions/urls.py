from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SubscriptionPlanViewSet, SubscriptionViewSet, TransactionViewSet, ReferralBonusViewSet

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'plans', SubscriptionPlanViewSet)
router.register(r'transactions', TransactionViewSet)
router.register(r'referral-bonuses', ReferralBonusViewSet)
router.register(r'', SubscriptionViewSet)

# The API URLs are now determined automatically by the router
urlpatterns = [
    path('', include(router.urls)),
]