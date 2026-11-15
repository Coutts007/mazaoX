from rest_framework import serializers

from apps.issues.models import Issue, IssueCategory


class IssueInputSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=IssueCategory.choices)
    description = serializers.CharField(max_length=2000)


class IssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Issue
        fields = ("id", "order_id", "category", "description", "status", "resolution", "created_at", "updated_at")
