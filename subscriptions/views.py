from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import SubscriptionPlan, Subscription, Transaction, ReferralBonus
from .serializers import (
    SubscriptionPlanSerializer, SubscriptionSerializer, SubscriptionCreateSerializer,
    TransactionSerializer, TransactionCreateSerializer, ReferralBonusSerializer
)
from users.permissions import IsAdminUser, IsOwnerOrAdmin


class SubscriptionPlanViewSet(viewsets.ModelViewSet):
    """
    ViewSet for SubscriptionPlan model.
    """
    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer
    
    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """
        Filter plans based on active status.
        """
        queryset = SubscriptionPlan.objects.all()
        
        # Admin users can see all plans, regular users only see active plans
        if not self.request.user.role == 'admin':
            queryset = queryset.filter(is_active=True)
        
        return queryset


class SubscriptionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Subscription model.
    """
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    
    def get_queryset(self):
        """
        Filter subscriptions based on user permissions.
        """
        if self.request.user.role == 'admin':
            return Subscription.objects.all()
        return Subscription.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        """
        Return appropriate serializer class based on the action.
        """
        if self.action == 'create':
            return SubscriptionCreateSerializer
        return SubscriptionSerializer
    
    def perform_create(self, serializer):
        """
        Set the user to the current user when creating a subscription.
        """
        serializer.save()
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancel a subscription.
        """
        subscription = self.get_object()
        
        if subscription.status != 'active':
            return Response({"error": "Only active subscriptions can be cancelled"}, status=status.HTTP_400_BAD_REQUEST)
        
        subscription.status = 'cancelled'
        subscription.save()
        
        serializer = self.get_serializer(subscription)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def renew(self, request, pk=None):
        """
        Renew a subscription.
        """
        subscription = self.get_object()
        
        if subscription.status not in ['expired', 'cancelled']:
            return Response({"error": "Only expired or cancelled subscriptions can be renewed"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Logic for renewing subscription would go here
        # This would typically involve creating a new transaction and updating dates
        
        subscription.status = 'active'
        subscription.save()
        
        serializer = self.get_serializer(subscription)
        return Response(serializer.data)


class TransactionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Transaction model.
    """
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    
    def get_queryset(self):
        """
        Filter transactions based on user permissions.
        """
        if self.request.user.role == 'admin':
            return Transaction.objects.all()
        return Transaction.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        """
        Return appropriate serializer class based on the action.
        """
        if self.action == 'create':
            return TransactionCreateSerializer
        return TransactionSerializer
    
    def perform_create(self, serializer):
        """
        Set the user to the current user when creating a transaction.
        """
        serializer.save()
    
    @action(detail=True, methods=['post'])
    def process_payment(self, request, pk=None):
        """
        Process a payment for a transaction.
        """
        transaction = self.get_object()
        
        if transaction.status != 'pending':
            return Response({"error": "Only pending transactions can be processed"}, status=status.HTTP_400_BAD_REQUEST)
        
        # In a real application, this would integrate with a payment gateway
        # For now, we'll just simulate a successful payment
        
        transaction.status = 'completed'
        transaction.save()
        
        # If this transaction is for a subscription, update the subscription
        if transaction.subscription:
            subscription = transaction.subscription
            subscription.status = 'active'
            subscription.save()
        
        serializer = self.get_serializer(transaction)
        return Response(serializer.data)


class ReferralBonusViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for ReferralBonus model.
    """
    queryset = ReferralBonus.objects.all()
    serializer_class = ReferralBonusSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    
    def get_queryset(self):
        """
        Filter referral bonuses based on user permissions.
        """
        if self.request.user.role == 'admin':
            return ReferralBonus.objects.all()
        return ReferralBonus.objects.filter(referrer=self.request.user)