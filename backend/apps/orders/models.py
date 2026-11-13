import uuid

from django.db import models
from django.db.models import Q


class OrderStatus(models.TextChoices):
    PENDING_PAYMENT = "pending_payment", "Pending payment"
    PAID = "paid", "Paid"
    CANCELLED = "cancelled", "Cancelled"
    EXPIRED = "expired", "Expired"


class DeliveryMethod(models.TextChoices):
    COLLECTION = "collection", "Collection"
    DELIVERY = "delivery", "Delivery"


class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer_id = models.UUIDField(db_index=True)
    farmer_id = models.UUIDField(db_index=True)  # one farmer per order
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING_PAYMENT, db_index=True)
    delivery_method = models.CharField(max_length=12, choices=DeliveryMethod.choices)
    delivery_location = models.CharField(max_length=255, blank=True)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2)  # KSh, calculated by the server
    idempotency_key = models.CharField(max_length=64, null=True, blank=True)
    request_hash = models.CharField(max_length=64, blank=True)  # detects key reuse with a different body
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["buyer_id", "idempotency_key"], condition=Q(idempotency_key__isnull=False),
                name="one_order_per_buyer_idempotency_key",
            ),
            models.CheckConstraint(condition=Q(total_amount__gt=0), name="order_total_positive"),
        ]


class OrderLine(models.Model):
    """Price, name and unit are snapshotted at order time so later listing edits never change an order."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="lines")
    listing_id = models.UUIDField()
    produce_name = models.CharField(max_length=120)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    quantity_unit = models.CharField(max_length=10)
    line_total = models.DecimalField(max_digits=14, decimal_places=2)
    reservation_id = models.UUIDField()  # inventory reservation, by value

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["order", "listing_id"], name="one_line_per_listing_per_order"),
            models.CheckConstraint(condition=Q(quantity__gt=0), name="orderline_quantity_positive"),
        ]


class OrderStatusHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="history")
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    actor_id = models.UUIDField(null=True, blank=True)  # null = system
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
