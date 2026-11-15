import uuid

from django.db import models


class InspectionResult(models.TextChoices):
    PASSED = "passed", "Passed"
    PASSED_WITH_NOTES = "passed_with_notes", "Passed with notes"
    FAILED = "failed", "Failed"


class Inspection(models.Model):
    """An INDEPENDENT inspection entered by an administrator. Not the farmer's own claim (that is declared_grade)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing_id = models.UUIDField(db_index=True)
    inspected_on = models.DateField()
    scope = models.CharField(max_length=255)  # what exactly was inspected (batch, quantity, date harvested...)
    result = models.CharField(max_length=20, choices=InspectionResult.choices)
    assessed_grade = models.CharField(max_length=80, blank=True)
    notes = models.CharField(max_length=1000, blank=True)
    inspector_id = models.UUIDField()
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-inspected_on", "-created_at"]


class InspectionRevision(models.Model):
    """Snapshot of an inspection before each correction (audit trail)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inspection = models.ForeignKey(Inspection, on_delete=models.CASCADE, related_name="revisions")
    snapshot = models.JSONField()
    changed_by = models.UUIDField()
    reason = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
