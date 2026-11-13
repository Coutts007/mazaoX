from rest_framework import serializers

from apps.inventory.models import MovementType, StockMovement


class AdjustmentSerializer(serializers.Serializer):
    movement_type = serializers.ChoiceField(choices=[MovementType.ADDITION, MovementType.CORRECTION, MovementType.SPOILAGE])
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3)
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True)


class MovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = ("id", "movement_type", "quantity_delta", "resulting_on_hand", "reason", "order_id", "created_at")


class SummarySerializer(serializers.Serializer):
    listing_id = serializers.UUIDField()
    unit = serializers.CharField()
    on_hand = serializers.DecimalField(max_digits=14, decimal_places=3)
    reserved = serializers.DecimalField(max_digits=14, decimal_places=3)
    available = serializers.DecimalField(max_digits=14, decimal_places=3)


class PublicAvailabilitySerializer(serializers.Serializer):
    listing_id = serializers.UUIDField()
    unit = serializers.CharField()
    available = serializers.DecimalField(max_digits=14, decimal_places=3)
    in_stock = serializers.SerializerMethodField()

    def get_in_stock(self, obj):
        return obj.available > 0
