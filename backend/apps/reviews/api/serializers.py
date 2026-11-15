from rest_framework import serializers


class ReviewInputSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(max_length=1000, required=False, allow_blank=True)


class ReviewSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    order_id = serializers.UUIDField()
    rating = serializers.IntegerField()
    comment = serializers.CharField()
    created_at = serializers.DateTimeField()
