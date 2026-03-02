from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for the Notification model.
    All fields are read-only except is_read, which users can toggle.
    """
    class Meta:
        model = Notification
        fields = (
            'id',
            'user',
            'type',
            'title',
            'message',
            'is_read',
            'data',
            'created_at',
        )
        read_only_fields = (
            'id',
            'user',
            'type',
            'title',
            'message',
            'data',
            'created_at',
        )
