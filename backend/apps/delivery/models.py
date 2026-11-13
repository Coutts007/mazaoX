import uuid

from django.db import models


class DeliveryStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    DISPATCHED = "dispatched", "Dispatched / ready for collection"
    DELIVERED = "delivered", "Delivered / collected"
    FAILED = "failed", "Failed"


class Delivery(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_id = models.UUIDField(unique=True)  # one delivery record per order
    buyer_id = models.UUIDField(db_index=True)
    farmer_id = models.UUIDField(db_index=True)
    method = models.CharField(max_length=12)  # collection | delivery, copied from the order
    location = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=12, choices=DeliveryStatus.choices, default=DeliveryStatus.PENDING)
    operator_id = models.UUIDField(null=True, blank=True)  # admin who created/last updated it
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class DeliveryEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE, related_name="events")
    from_status = models.CharField(max_length=12, blank=True)
    to_status = models.CharField(max_length=12)
    actor_id = models.UUIDField(null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
