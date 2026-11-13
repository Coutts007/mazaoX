from rest_framework import serializers

from apps.orders import selectors
from apps.orders.models import DeliveryMethod, Order, OrderLine, OrderStatusHistory


class OrderItemInputSerializer(serializers.Serializer):
    listing_id = serializers.UUIDField()
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=0)
    quantity_unit = serializers.CharField(max_length=10)


class OrderInputSerializer(serializers.Serializer):
    # Prices and totals are deliberately not accepted: the server calculates them.
    items = OrderItemInputSerializer(many=True, allow_empty=False)
    delivery_method = serializers.ChoiceField(choices=DeliveryMethod.choices)
    delivery_location = serializers.CharField(max_length=255, required=False, allow_blank=True)


class OrderLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderLine
        fields = ("listing_id", "produce_name", "unit_price", "quantity", "quantity_unit", "line_total")


class OrderSerializer(serializers.ModelSerializer):
    lines = OrderLineSerializer(many=True, read_only=True)
    payment_due_by = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            "id", "buyer_id", "farmer_id", "status", "delivery_method", "delivery_location",
            "total_amount", "currency", "lines", "payment_due_by", "created_at", "updated_at",
        )

    currency = serializers.SerializerMethodField()

    def get_currency(self, obj):
        return "KSh"

    def get_payment_due_by(self, obj):
        return selectors.payment_due_by(obj)


class CancelSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True)


class HistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusHistory
        fields = ("from_status", "to_status", "note", "created_at")
