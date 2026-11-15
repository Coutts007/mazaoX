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
