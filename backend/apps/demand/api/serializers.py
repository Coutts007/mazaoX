from rest_framework import serializers

from apps.catalogue.api.serializers import ListingSerializer
from apps.demand.models import DemandRequest


class DemandInputSerializer(serializers.Serializer):
    produce_name = serializers.CharField(max_length=120)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=0)
    quantity_unit = serializers.CharField(max_length=10)
    target_price_per_unit = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, required=False, allow_null=True)
    county = serializers.CharField(max_length=40)
    required_by = serializers.DateField()


class DemandSerializer(serializers.ModelSerializer):
    class Meta:
        model = DemandRequest
        fields = ("id", "produce_name", "quantity", "quantity_unit", "target_price_per_unit", "county", "required_by", "status", "created_at")


class MarketDemandSerializer(DemandSerializer):
    """What farmers see: the need, never who posted it."""


class MatchSerializer(serializers.Serializer):
    score = serializers.IntegerField()
    reasons = serializers.ListField(child=serializers.CharField())
    available = serializers.DecimalField(max_digits=14, decimal_places=3)
    listing = serializers.SerializerMethodField()

    def get_listing(self, obj):
        return ListingSerializer(obj.listing).data
