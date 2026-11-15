from rest_framework import serializers

from apps.quality.models import Inspection, InspectionResult


class InspectionInputSerializer(serializers.Serializer):
    inspected_on = serializers.DateField()
    scope = serializers.CharField(max_length=255)
    result = serializers.ChoiceField(choices=InspectionResult.choices)
    assessed_grade = serializers.CharField(max_length=80, required=False, allow_blank=True)
    notes = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    is_published = serializers.BooleanField(required=False)


class InspectionSerializer(serializers.ModelSerializer):
    # Always labelled so clients never confuse it with the farmer's own declared grade.
    source = serializers.SerializerMethodField()

    class Meta:
        model = Inspection
        fields = ("id", "listing_id", "source", "inspected_on", "scope", "result", "assessed_grade", "notes", "is_published", "updated_at")

    def get_source(self, obj):
        return "independent_inspection"


class CorrectionSerializer(InspectionInputSerializer):
    reason = serializers.CharField(max_length=255)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != "reason":
                field.required = False
