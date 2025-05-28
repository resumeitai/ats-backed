from rest_framework import serializers
from .models import SubscriptionPlan, Subscription, Transaction, ReferralBonus
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