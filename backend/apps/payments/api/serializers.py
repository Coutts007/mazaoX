from rest_framework import serializers

from apps.payments.models import PaymentAttempt


class PaymentAttemptSerializer(serializers.ModelSerializer):
    mode = serializers.SerializerMethodField()

    class Meta:
        model = PaymentAttempt
        fields = ("id", "order_id", "amount", "currency", "status", "failure_reason", "mode", "created_at", "completed_at")

    def get_mode(self, obj):
        return "simulated"


class CompleteSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=["success", "failure"])
