from rest_framework import serializers

from apps.catalogue.models import Category, Listing, ListingMedia, QuantityUnit


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug")


class ListingInputSerializer(serializers.Serializer):
    category_id = serializers.UUIDField()
    produce_name = serializers.CharField(max_length=120)
    variety = serializers.CharField(max_length=120, required=False, allow_blank=True)
    description = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    declared_grade = serializers.CharField(max_length=80, required=False, allow_blank=True)
    price_per_unit = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    quantity_unit = serializers.ChoiceField(choices=QuantityUnit.choices)
    county = serializers.CharField(max_length=40)
    locality = serializers.CharField(max_length=100, required=False, allow_blank=True)
    harvest_date = serializers.DateField(required=False, allow_null=True)


class MediaSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ListingMedia
        fields = ("id", "url", "width", "height", "position")

    def get_url(self, obj):
        return f"/api/v1/media/{obj.id}"


class ListingSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    images = MediaSerializer(source="media", many=True, read_only=True)
    availability = serializers.SerializerMethodField()
    # Quality shown here is the farmer's own claim; the UI must never present it as verified.
    grade_source = serializers.SerializerMethodField()
    grade_verified = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = (
            "id", "farmer_id", "category", "produce_name", "variety", "description",
            "declared_grade", "grade_source", "grade_verified", "images", "availability", "price_per_unit",
            "quantity_unit", "county", "locality", "harvest_date", "status", "moderation_hidden", "moderation_reason",
            "created_at", "updated_at",
        )

    def get_availability(self, obj):
        """Filled from the list/detail view (batch lookup) so the serializer never queries inventory per row."""
        available = self.context.get("availability", {}).get(str(obj.id))
        if available is None:
            return None
        return {"available": f"{available:.3f}", "in_stock": available > 0}

    def get_grade_source(self, obj):
        return "farmer_declared"

    def get_grade_verified(self, obj):
        return False


class ListingFilterSerializer(serializers.Serializer):
    q = serializers.CharField(required=False, max_length=100)
    category_id = serializers.UUIDField(required=False)
    county = serializers.CharField(required=False, max_length=40)
    locality = serializers.CharField(required=False, max_length=100)
    min_price = serializers.DecimalField(required=False, max_digits=12, decimal_places=2, min_value=0)
    max_price = serializers.DecimalField(required=False, max_digits=12, decimal_places=2, min_value=0)
    quantity_unit = serializers.ChoiceField(required=False, choices=QuantityUnit.choices)
    declared_grade = serializers.CharField(required=False, max_length=80)
    mine = serializers.BooleanField(required=False)
    min_quantity = serializers.DecimalField(required=False, max_digits=12, decimal_places=3, min_value=0)
    ordering = serializers.ChoiceField(required=False, choices=["newest", "price_asc", "price_desc", "harvest_newest"])

    def validate(self, attrs):
        lo, hi = attrs.get("min_price"), attrs.get("max_price")
        if lo is not None and hi is not None and lo > hi:
            raise serializers.ValidationError({"min_price": "min_price cannot exceed max_price."})
        return attrs
