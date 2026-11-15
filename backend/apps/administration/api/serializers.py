from rest_framework import serializers


class AdminUserSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    full_name = serializers.CharField()
    email = serializers.EmailField(allow_null=True)
    phone = serializers.CharField(allow_null=True)
    role = serializers.CharField()
    is_active = serializers.BooleanField()
    date_joined = serializers.DateTimeField()


class UserStatusSerializer(serializers.Serializer):
    is_active = serializers.BooleanField()
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True)


class ModerationSerializer(serializers.Serializer):
    hidden = serializers.BooleanField()
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True)


class IssueUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["open", "investigating", "resolved", "dismissed"])
    resolution = serializers.CharField(max_length=2000, required=False, allow_blank=True)


class AdminReviewSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    order_id = serializers.UUIDField()
    farmer_id = serializers.UUIDField()
    rating = serializers.IntegerField()
    comment = serializers.CharField()
    is_hidden = serializers.BooleanField()
    moderation_reason = serializers.CharField()
    created_at = serializers.DateTimeField()


class AuditLogSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    actor_id = serializers.UUIDField(allow_null=True)
    action = serializers.CharField()
    target_type = serializers.CharField()
    target_id = serializers.CharField()
    detail = serializers.JSONField()
    created_at = serializers.DateTimeField()


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


class AdminListingSerializer(serializers.Serializer):
    """Renders catalogue's ListingSummary DTO. Administration owns its own representation."""

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
        return None  # stock levels belong to inventory; the moderation view does not show them


class AdminIssueSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    order_id = serializers.UUIDField()
    category = serializers.CharField()
    description = serializers.CharField()
    status = serializers.CharField()
    resolution = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
