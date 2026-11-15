from rest_framework import serializers

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


class _CategorySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.CharField()


class _ImageSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    url = serializers.CharField()
    width = serializers.IntegerField()
    height = serializers.IntegerField()
    position = serializers.IntegerField()


class MatchedListingSerializer(serializers.Serializer):
    """Renders catalogue's ListingSummary DTO (demand does not use catalogue's serializers or models)."""

    id = serializers.UUIDField()
    farmer_id = serializers.UUIDField()
    category = _CategorySerializer()
    produce_name = serializers.CharField()
    variety = serializers.CharField()
    description = serializers.CharField()
    declared_grade = serializers.CharField()
    grade_source = serializers.CharField()
    grade_verified = serializers.BooleanField()
    images = _ImageSerializer(many=True)
    availability = serializers.SerializerMethodField()
    price_per_unit = serializers.DecimalField(max_digits=12, decimal_places=2)
    quantity_unit = serializers.CharField()
    county = serializers.CharField()
    locality = serializers.CharField()
    harvest_date = serializers.DateField(allow_null=True)
    status = serializers.CharField()
    moderation_hidden = serializers.BooleanField()
    moderation_reason = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()

    def get_availability(self, obj):
        return None


class MatchSerializer(serializers.Serializer):
    score = serializers.IntegerField()
    reasons = serializers.ListField(child=serializers.CharField())
    available = serializers.DecimalField(max_digits=14, decimal_places=3)
    listing = serializers.SerializerMethodField()

    def get_listing(self, obj):
        return MatchedListingSerializer(obj.listing).data
