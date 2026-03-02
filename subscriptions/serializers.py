from rest_framework import serializers
from .models import SubscriptionPlan, Subscription, Transaction, ReferralBonus, PromotionalOffer, Invoice
from users.serializers import UserSerializer


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """
    Serializer for the SubscriptionPlan model.
    """
    class Meta:
        model = SubscriptionPlan
        fields = ('id', 'name', 'description', 'price', 'duration_months', 'features', 'is_active', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class SubscriptionSerializer(serializers.ModelSerializer):
    """
    Serializer for the Subscription model.
    """
    user = UserSerializer(read_only=True)
    plan = SubscriptionPlanSerializer(read_only=True)
    plan_id = serializers.PrimaryKeyRelatedField(
        queryset=SubscriptionPlan.objects.all(),
        source='plan',
        write_only=True
    )
    
    class Meta:
        model = Subscription
        fields = ('id', 'user', 'plan', 'plan_id', 'status', 'start_date', 'end_date', 'is_auto_renew', 'created_at', 'updated_at')
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')


class SubscriptionCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a subscription.
    """
    class Meta:
        model = Subscription
        fields = ('plan', 'is_auto_renew')
    
    def create(self, validated_data):
        user = self.context['request'].user
        subscription = Subscription.objects.create(user=user, **validated_data)
        return subscription


class TransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for the Transaction model.
    """
    user = UserSerializer(read_only=True)
    subscription = SubscriptionSerializer(read_only=True)
    
    class Meta:
        model = Transaction
        fields = ('id', 'user', 'subscription', 'amount', 'currency', 'payment_method', 'status', 
                  'transaction_id', 'payment_gateway_response', 'created_at', 'updated_at')
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')


class TransactionCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a transaction.
    """
    subscription_id = serializers.PrimaryKeyRelatedField(
        queryset=Subscription.objects.all(),
        source='subscription',
        required=False
    )
    
    class Meta:
        model = Transaction
        fields = ('subscription_id', 'amount', 'currency', 'payment_method')
    
    def create(self, validated_data):
        user = self.context['request'].user
        transaction = Transaction.objects.create(user=user, status='pending', **validated_data)
        return transaction


class ReferralBonusSerializer(serializers.ModelSerializer):
    """
    Serializer for the ReferralBonus model.
    """
    referrer = UserSerializer(read_only=True)

    class Meta:
        model = ReferralBonus
        fields = ('id', 'referrer', 'referral', 'subscription', 'bonus_months', 'is_applied', 'created_at')
        read_only_fields = ('id', 'referrer', 'created_at')


class CreateOrderSerializer(serializers.Serializer):
    """
    Serializer for creating a Razorpay order.
    """
    plan_id = serializers.PrimaryKeyRelatedField(queryset=SubscriptionPlan.objects.all())
    promo_code = serializers.CharField(required=False, allow_blank=True)


class VerifyPaymentSerializer(serializers.Serializer):
    """
    Serializer for verifying a Razorpay payment.
    """
    razorpay_order_id = serializers.CharField()
    razorpay_payment_id = serializers.CharField()
    razorpay_signature = serializers.CharField()
    subscription_id = serializers.PrimaryKeyRelatedField(queryset=Subscription.objects.all())


class PromoCodeSerializer(serializers.Serializer):
    """
    Serializer for applying a promo code.
    """
    code = serializers.CharField()


class PromotionalOfferSerializer(serializers.ModelSerializer):
    """
    Serializer for the PromotionalOffer model.
    """
    class Meta:
        model = PromotionalOffer
        fields = (
            'id', 'code', 'discount_percentage', 'valid_from', 'valid_until',
            'max_uses', 'current_uses', 'applicable_plans', 'is_active',
        )
        read_only_fields = ('id', 'current_uses')


class InvoiceSerializer(serializers.ModelSerializer):
    """
    Serializer for the Invoice model.
    """
    class Meta:
        model = Invoice
        fields = ('id', 'transaction', 'invoice_number', 'pdf_file', 'created_at')
        read_only_fields = ('id', 'created_at')