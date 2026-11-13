import uuid

from django.db import models
from django.db.models import Q


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"


class PaymentAttempt(models.Model):
    """A SIMULATED payment attempt. Holds no phone numbers, PINs, card data or other credentials."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_id = models.UUIDField(db_index=True)  # orders domain, by value
    buyer_id = models.UUIDField(db_index=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)  # copied from the order by the server
    currency = models.CharField(max_length=3, default="KSh")
    status = models.CharField(max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    failure_reason = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["order_id"], condition=Q(status="pending"), name="one_pending_payment_per_order"),
            models.UniqueConstraint(fields=["order_id"], condition=Q(status="succeeded"), name="one_successful_payment_per_order"),
            models.CheckConstraint(condition=Q(amount__gt=0), name="payment_amount_positive"),
        ]
