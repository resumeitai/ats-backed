import hashlib
import hmac
import logging
from datetime import timedelta
from decimal import Decimal

from django.db.models import F
from rest_framework import viewsets, generics, views, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .models import SubscriptionPlan, Subscription, Transaction, ReferralBonus, PromotionalOffer
from .serializers import (
    SubscriptionPlanSerializer, SubscriptionSerializer, SubscriptionCreateSerializer,
    TransactionSerializer, TransactionCreateSerializer, ReferralBonusSerializer,
    CreateOrderSerializer, VerifyPaymentSerializer, PromoCodeSerializer,
)
from .payment_gateways import RazorpayGateway
from users.permissions import IsAdminUser, IsOwnerOrAdmin

logger = logging.getLogger(__name__)


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


class CreateOrderView(generics.GenericAPIView):
    """
    Creates a Razorpay order for a subscription plan.
    POST: expects plan_id and optional promo_code.
    Returns order details to frontend for checkout.
    """
    serializer_class = CreateOrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        plan = serializer.validated_data['plan_id']
        promo_code = serializer.validated_data.get('promo_code', '')
        amount = plan.price

        # Apply promo code discount if provided
        discount = Decimal('0')
        if promo_code:
            try:
                now = timezone.now()
                offer = PromotionalOffer.objects.get(
                    code=promo_code,
                    is_active=True,
                    valid_from__lte=now,
                    valid_until__gte=now,
                    current_uses__lt=F('max_uses'),
                )
                # Check if the promo applies to this plan
                if offer.applicable_plans.exists() and not offer.applicable_plans.filter(pk=plan.pk).exists():
                    return Response(
                        {'error': 'This promo code is not applicable to the selected plan.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                discount = amount * Decimal(offer.discount_percentage) / Decimal('100')
                amount = amount - discount
            except PromotionalOffer.DoesNotExist:
                return Response(
                    {'error': 'Invalid or expired promo code.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Create Razorpay order
        gateway = RazorpayGateway()
        try:
            order = gateway.create_order(
                amount=float(amount),
                currency='INR',
                metadata={
                    'plan_id': str(plan.pk),
                    'user_id': str(request.user.pk),
                    'promo_code': promo_code,
                },
            )
        except Exception as e:
            logger.error(f'Razorpay order creation failed: {e}')
            return Response(
                {'error': 'Failed to create payment order. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Create a pending subscription
        subscription = Subscription.objects.create(
            user=request.user,
            plan=plan,
            status='pending',
        )

        # Create a pending transaction
        Transaction.objects.create(
            user=request.user,
            subscription=subscription,
            amount=amount,
            currency='INR',
            payment_method='upi',
            status='pending',
            payment_gateway='razorpay',
            gateway_order_id=order['id'],
            payment_gateway_response=order,
        )

        return Response({
            'order_id': order['id'],
            'amount': order['amount'],
            'currency': order['currency'],
            'status': order['status'],
            'subscription_id': subscription.pk,
            'key_id': settings.RAZORPAY_KEY_ID,
        }, status=status.HTTP_201_CREATED)


class VerifyPaymentView(generics.GenericAPIView):
    """
    Verifies a Razorpay payment, activates the subscription, and updates the transaction.
    """
    serializer_class = VerifyPaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        razorpay_order_id = serializer.validated_data['razorpay_order_id']
        razorpay_payment_id = serializer.validated_data['razorpay_payment_id']
        razorpay_signature = serializer.validated_data['razorpay_signature']
        subscription = serializer.validated_data['subscription_id']

        # Verify payment signature
        gateway = RazorpayGateway()
        is_valid = gateway.verify_payment({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature,
        })

        if not is_valid:
            return Response(
                {'error': 'Payment verification failed. Invalid signature.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update transaction
        try:
            transaction = Transaction.objects.get(
                gateway_order_id=razorpay_order_id,
                user=request.user,
            )
        except Transaction.DoesNotExist:
            return Response(
                {'error': 'Transaction not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        transaction.transaction_id = razorpay_payment_id
        transaction.status = 'completed'
        transaction.payment_gateway_response = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature,
        }
        transaction.save()

        # Activate subscription
        now = timezone.now().date()
        subscription.status = 'active'
        subscription.start_date = now
        subscription.end_date = now + timedelta(days=subscription.plan.duration_months * 30)
        subscription.save()

        # Increment promo code usage if applicable
        promo_code = transaction.payment_gateway_response.get('promo_code', '')
        if not promo_code and isinstance(transaction.payment_gateway_response, dict):
            # Check the original order metadata stored in the first response
            pass

        return Response({
            'message': 'Payment verified successfully.',
            'subscription_id': subscription.pk,
            'subscription_status': subscription.status,
            'transaction_id': transaction.transaction_id,
        }, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class RazorpayWebhookView(views.APIView):
    """
    Handles Razorpay webhooks.
    CSRF exempt and allows any user (no auth required for webhooks).
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        # Verify webhook signature
        webhook_secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', '')
        webhook_signature = request.headers.get('X-Razorpay-Signature', '')
        webhook_body = request.body

        if webhook_secret:
            expected_signature = hmac.new(
                key=webhook_secret.encode('utf-8'),
                msg=webhook_body,
                digestmod=hashlib.sha256,
            ).hexdigest()

            if not hmac.compare_digest(expected_signature, webhook_signature):
                logger.warning('Invalid Razorpay webhook signature.')
                return Response(
                    {'error': 'Invalid webhook signature.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        payload = request.data
        event = payload.get('event', '')

        if event == 'payment.captured':
            payment_entity = payload.get('payload', {}).get('payment', {}).get('entity', {})
            order_id = payment_entity.get('order_id', '')
            payment_id = payment_entity.get('id', '')

            try:
                transaction = Transaction.objects.get(gateway_order_id=order_id)
                if transaction.status != 'completed':
                    transaction.status = 'completed'
                    transaction.transaction_id = payment_id
                    transaction.save()

                    # Activate subscription
                    subscription = transaction.subscription
                    if subscription and subscription.status == 'pending':
                        now = timezone.now().date()
                        subscription.status = 'active'
                        subscription.start_date = now
                        subscription.end_date = now + timedelta(days=subscription.plan.duration_months * 30)
                        subscription.save()
            except Transaction.DoesNotExist:
                logger.warning(f'Webhook: Transaction not found for order_id {order_id}')

        elif event == 'payment.failed':
            payment_entity = payload.get('payload', {}).get('payment', {}).get('entity', {})
            order_id = payment_entity.get('order_id', '')

            try:
                transaction = Transaction.objects.get(gateway_order_id=order_id)
                transaction.status = 'failed'
                transaction.save()
            except Transaction.DoesNotExist:
                logger.warning(f'Webhook: Transaction not found for order_id {order_id}')

        elif event == 'refund.created':
            refund_entity = payload.get('payload', {}).get('refund', {}).get('entity', {})
            payment_id = refund_entity.get('payment_id', '')
            refund_id = refund_entity.get('id', '')
            refund_amount = refund_entity.get('amount', 0) / 100  # Convert paise to rupees

            try:
                transaction = Transaction.objects.get(transaction_id=payment_id)
                transaction.refund_id = refund_id
                transaction.refund_amount = Decimal(str(refund_amount))
                transaction.refund_status = 'processed'
                transaction.status = 'refunded'
                transaction.save()
            except Transaction.DoesNotExist:
                logger.warning(f'Webhook: Transaction not found for payment_id {payment_id}')

        return Response({'status': 'ok'}, status=status.HTTP_200_OK)


class ApplyPromoCodeView(generics.GenericAPIView):
    """
    Validates a promo code and returns discount info.
    """
    serializer_class = PromoCodeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code = serializer.validated_data['code']
        now = timezone.now()

        try:
            offer = PromotionalOffer.objects.get(
                code=code,
                is_active=True,
                valid_from__lte=now,
                valid_until__gte=now,
            )
        except PromotionalOffer.DoesNotExist:
            return Response(
                {'error': 'Invalid or expired promo code.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if offer.current_uses >= offer.max_uses:
            return Response(
                {'error': 'This promo code has reached its usage limit.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        applicable_plan_ids = list(offer.applicable_plans.values_list('id', flat=True))

        return Response({
            'code': offer.code,
            'discount_percentage': offer.discount_percentage,
            'applicable_plans': applicable_plan_ids if applicable_plan_ids else 'all',
            'valid_until': offer.valid_until,
        }, status=status.HTTP_200_OK)