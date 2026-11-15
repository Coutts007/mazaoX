import uuid

from django.db import models


class IssueCategory(models.TextChoices):
    QUALITY = "quality", "Quality of produce"
    DELIVERY = "delivery", "Delivery problem"
    PAYMENT = "payment", "Payment problem"
    OTHER = "other", "Other"


class IssueStatus(models.TextChoices):
    OPEN = "open", "Open"
    INVESTIGATING = "investigating", "Investigating"
    RESOLVED = "resolved", "Resolved"
    DISMISSED = "dismissed", "Dismissed"


class Issue(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_id = models.UUIDField(db_index=True)
    reporter_id = models.UUIDField(db_index=True)
    category = models.CharField(max_length=12, choices=IssueCategory.choices)
    description = models.CharField(max_length=2000)
    status = models.CharField(max_length=14, choices=IssueStatus.choices, default=IssueStatus.OPEN, db_index=True)
    resolution = models.CharField(max_length=2000, blank=True)
    handled_by = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
