import uuid

from django.db import models


class Notification(models.Model):
    """In-app notification. The recipient is referenced by id; the source transaction lives elsewhere."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient_id = models.UUIDField()
    kind = models.CharField(max_length=40)  # e.g. order_placed, payment_received
    title = models.CharField(max_length=120)
    message = models.CharField(max_length=255)
    order_id = models.UUIDField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["recipient_id", "is_read"])]
