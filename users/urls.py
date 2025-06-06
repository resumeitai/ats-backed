from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, UserActivityViewSet, ReferralViewSet,
    RegisterView, OTPVerificationView, ResendOTPView
)

router = DefaultRouter()
router.register(r'', UserViewSet)
router.register(r'activities', UserActivityViewSet)
router.register(r'referrals', ReferralViewSet)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('verify-email/', OTPVerificationView.as_view(), name='verify-email'),
    path('resend-verification/', ResendOTPView.as_view(), name='resend-verification'),
    path('', include(router.urls)),

]