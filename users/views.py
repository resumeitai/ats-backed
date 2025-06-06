from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from django.conf import settings
import uuid
from .models import UserActivity, Referral
from .serializers import (
    UserSerializer, UserRegistrationSerializer, UserActivitySerializer,
    ReferralSerializer, ReferralCreateSerializer, OTPVerificationSerializer,
    ResendOTPSerializer
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

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        
        try:
            user = User.objects.get(email=email, is_verified=False)
            
            # Generate new OTP
            otp = user.generate_otp()
            
            # Send OTP email
            subject = "Your OTP for Email Verification - ResumeIt"
            message = f"""
            Hello {user.full_name or user.username},
            
            Your OTP for email verification is: {otp}
            
            This OTP will expire in 10 minutes.
            
            If you didn't request this, please ignore this email.
            
            Best regards,
            The ResumeIt Team
            """
            
            html_message = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #007bff; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; background-color: #f9f9f9; }}
                    .otp-box {{ background-color: #007bff; color: white; font-size: 24px; font-weight: bold; text-align: center; padding: 20px; margin: 20px 0; border-radius: 5px; letter-spacing: 5px; }}
                    .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #666; }}
                    .warning {{ background-color: #fff3cd; color: #856404; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Email Verification OTP</h1>
                    </div>
                    <div class="content">
                        <h2>Hello {user.full_name or user.username},</h2>
                        <p>Your OTP for email verification is:</p>
                        <div class="otp-box">{otp}</div>
                        <div class="warning">
                            <strong>Important:</strong> This OTP will expire in 10 minutes. Please use it as soon as possible.
                        </div>
                        <p>If you didn't request this OTP, please ignore this email.</p>
                    </div>
                    <div class="footer">
                        <p>Best regards,<br>The ResumeIt Team</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            return Response(
                {"message": "OTP sent successfully to your email!"},
                status=status.HTTP_200_OK
            )
            
        except User.DoesNotExist:
            return Response(
                {"error": "User with this email not found or already verified."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": "Failed to send OTP. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )