import uuid

from django.db import models
from django.db.models import Q


class DemandStatus(models.TextChoices):
    OPEN = "open", "Open"
    CLOSED = "closed", "Closed"
    EXPIRED = "expired", "Expired"


class DemandRequest(models.Model):
    """What a buyer is looking for. Matching is informational and never creates orders or reservations."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer_id = models.UUIDField(db_index=True)
    produce_name = models.CharField(max_length=120)
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    quantity_unit = models.CharField(max_length=10)
    target_price_per_unit = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    county = models.CharField(max_length=40)
    required_by = models.DateField()
    status = models.CharField(max_length=10, choices=DemandStatus.choices, default=DemandStatus.OPEN, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [models.CheckConstraint(condition=Q(quantity__gt=0), name="demand_quantity_positive")]
