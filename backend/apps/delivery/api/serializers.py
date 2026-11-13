from rest_framework import serializers

from apps.delivery.models import Delivery, DeliveryEvent, DeliveryStatus


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryEvent
        fields = ("from_status", "to_status", "note", "created_at")


class DeliverySerializer(serializers.ModelSerializer):
    events = EventSerializer(many=True, read_only=True)

    class Meta:
        model = Delivery
        fields = ("id", "order_id", "method", "location", "status", "events", "created_at", "updated_at")


class StatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=DeliveryStatus.choices)
    note = serializers.CharField(max_length=255, required=False, allow_blank=True)
