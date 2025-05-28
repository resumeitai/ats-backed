from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from .models import UserActivity, Referral
from .serializers import (
    UserSerializer, UserRegistrationSerializer, UserActivitySerializer,
    ReferralSerializer, ReferralCreateSerializer
)
from .permissions import IsAdminUser, IsOwnerOrAdmin

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