from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import UserActivity, Referral

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the User model.
    """
    is_subscribed = serializers.ReadOnlyField()  
    subscription_status = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'full_name', 'phone_number', 'role', 
                 'is_verified', 'is_subscribed', 'subscription_status', 'created_at')
        read_only_fields = ('id', 'role', 'is_verified', 'is_subscribed', 'subscription_status', 'created_at')
    
    def get_subscription_status(self, obj):
        """
        Get detailed subscription status using the model method.
        """
        return obj.get_subscription_status()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    """
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'full_name', 'phone_number', 'password', 'password2')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user


class EmailVerificationSerializer(serializers.Serializer):
    """
    Serializer for email verification.
    """
    token = serializers.UUIDField()

    def validate_token(self, value):
        try:
            user = User.objects.get(email_verification_token=value, is_verified=False)
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired verification token.")


class ResendVerificationSerializer(serializers.Serializer):
    """
    Serializer for resending email verification.
    """
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = User.objects.get(email=value, is_verified=False)
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this email not found or already verified.")


class UserActivitySerializer(serializers.ModelSerializer):
    """
    Serializer for the UserActivity model.
    """
    user = UserSerializer(read_only=True)

    class Meta:
        model = UserActivity
        fields = ('id', 'user', 'activity_type', 'description', 'created_at')
        read_only_fields = ('id', 'created_at')


class ReferralSerializer(serializers.ModelSerializer):
    """
    Serializer for the Referral model.
    """
    referrer = UserSerializer(read_only=True)
    referred = UserSerializer(read_only=True)

    class Meta:
        model = Referral
        fields = ('id', 'referrer', 'referred', 'code', 'is_successful', 'created_at')
        read_only_fields = ('id', 'referrer', 'referred', 'is_successful', 'created_at')


class ReferralCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a referral.
    """
    email = serializers.EmailField(write_only=True)

    class Meta:
        model = Referral
        fields = ('email', 'code')

    def create(self, validated_data):
        email = validated_data.pop('email')
        referrer = self.context['request'].user
        
        referral = Referral.objects.create(
            referrer=referrer,
            referred=None, 
            **validated_data
        )
        
        # Send invitation email (to be implemented in views)
        
        return referral