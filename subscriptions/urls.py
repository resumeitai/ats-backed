from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SubscriptionPlanViewSet, SubscriptionViewSet, TransactionViewSet, ReferralBonusViewSet,
    CreateOrderView, VerifyPaymentView, RazorpayWebhookView, ApplyPromoCodeView,
)

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'plans', SubscriptionPlanViewSet)
router.register(r'transactions', TransactionViewSet)
router.register(r'referral-bonuses', ReferralBonusViewSet)
router.register(r'', SubscriptionViewSet)

# The API URLs are now determined automatically by the router
urlpatterns = [
    path('create-order/', CreateOrderView.as_view(), name='create-order'),
    path('verify-payment/', VerifyPaymentView.as_view(), name='verify-payment'),
    path('webhook/razorpay/', RazorpayWebhookView.as_view(), name='razorpay-webhook'),
    path('apply-promo/', ApplyPromoCodeView.as_view(), name='apply-promo'),
    path('', include(router.urls)),
]