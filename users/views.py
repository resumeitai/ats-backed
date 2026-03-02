from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .models import UserActivity, Referral
from .serializers import (
    UserSerializer, UserRegistrationSerializer, UserActivitySerializer,
    ReferralSerializer, ReferralCreateSerializer, OTPVerificationSerializer,
    ResendOTPSerializer, PasswordResetRequestSerializer, PasswordResetConfirmSerializer
)
from .permissions import IsAdminUser, IsOwnerOrAdmin, IsVerifiedUser

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for User model.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action == 'create':
            permission_classes = [permissions.AllowAny]
        elif self.action in ['list', 'retrieve', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsOwnerOrAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        """
        Return appropriate serializer class based on the action.
        """
        if self.action == 'create':
            return UserRegistrationSerializer
        return UserSerializer

    @action(detail=False, methods=['get'])
    def me(self, request):
        """
        Get the current user's profile.
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def activities(self, request, pk=None):
        """
        Get activities for a specific user.
        """
        user = self.get_object()
        activities = UserActivity.objects.filter(user=user)
        serializer = UserActivitySerializer(activities, many=True)
        return Response(serializer.data)


class UserActivityViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for UserActivity model.
    """
    queryset = UserActivity.objects.all()
    serializer_class = UserActivitySerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        """
        Filter activities based on user permissions.
        """
        if self.request.user.role == 'admin':
            return UserActivity.objects.all()
        return UserActivity.objects.filter(user=self.request.user)


class ReferralViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Referral model.
    """
    queryset = Referral.objects.all()
    serializer_class = ReferralSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        """
        Return appropriate serializer class based on the action.
        """
        if self.action == 'create':
            return ReferralCreateSerializer
        return ReferralSerializer

    def get_queryset(self):
        """
        Filter referrals based on user permissions.
        """
        if self.request.user.role == 'admin':
            return Referral.objects.all()
        return Referral.objects.filter(referrer=self.request.user)

    def perform_create(self, serializer):
        """
        Set the referrer to the current user when creating a referral.
        """
        serializer.save()

    @action(detail=False, methods=['get'])
    def my_referrals(self, request):
        """
        Get referrals made by the current user.
        """
        referrals = Referral.objects.filter(referrer=request.user)
        serializer = ReferralSerializer(referrals, many=True)
        return Response(serializer.data)


class RegisterView(generics.CreateAPIView):
    """
    API view for user registration.
    """
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'auth'

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response(
            {
                "message": "User registered successfully. Please check your email to verify your account.",
                "user_id": user.id,
                "email": user.email
            },
            status=status.HTTP_201_CREATED
        )


class OTPVerificationView(generics.GenericAPIView):
    """
    API view for OTP verification.
    """
    serializer_class = OTPVerificationSerializer
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'auth'

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        
        # Mark user as verified
        user.is_verified = True
        user.clear_otp()  # Clear OTP data
        user.save()
        
        # Create activity record
        UserActivity.objects.create(
            user=user,
            activity_type='email_verified',
            description='User verified their email address with OTP'
        )
        
        return Response(
            {"message": "Email verified successfully!"},
            status=status.HTTP_200_OK
        )


class ResendOTPView(generics.GenericAPIView):
    """
    API view for resending OTP.
    """
    serializer_class = ResendOTPSerializer
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'auth'

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email, is_verified=False)
            user.generate_otp()

            from .tasks import send_otp_email_task
            send_otp_email_task.delay(user.id)

            return Response(
                {"message": "OTP sent successfully to your email!"},
                status=status.HTTP_200_OK
            )

        except User.DoesNotExist:
            return Response(
                {"error": "User with this email not found or already verified."},
                status=status.HTTP_400_BAD_REQUEST
            )


class PasswordResetRequestView(generics.GenericAPIView):
    """API view for requesting a password reset OTP."""
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'auth'

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        user = User.objects.get(email=email)
        user.generate_password_reset_otp()

        from .tasks import send_password_reset_email_task
        send_password_reset_email_task.delay(user.id)

        return Response(
            {"message": "Password reset OTP sent to your email."},
            status=status.HTTP_200_OK
        )


class PasswordResetConfirmView(generics.GenericAPIView):
    """API view for confirming password reset with OTP."""
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'auth'

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        user.set_password(serializer.validated_data['new_password'])
        user.clear_password_reset_otp()
        user.save()

        UserActivity.objects.create(
            user=user,
            activity_type='password_reset',
            description='User reset their password via OTP'
        )

        return Response(
            {"message": "Password reset successfully."},
            status=status.HTTP_200_OK
        )