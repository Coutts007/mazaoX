import uuid

from django.db import models
from django.db.models import Q


class StockItem(models.Model):
    """Authoritative on-hand stock of one listing. Only inventory.services changes it."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing_id = models.UUIDField(unique=True)  # catalogue listing, by value
    farmer_id = models.UUIDField(db_index=True)
    unit = models.CharField(max_length=10)
    on_hand = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(on_hand__gte=0), name="stock_on_hand_not_negative")]


class MovementType(models.TextChoices):
    ADDITION = "addition", "Addition"
    CORRECTION = "correction", "Manual correction"
    SPOILAGE = "spoilage", "Spoilage / loss"
    SALE = "sale", "Sale (reservation committed)"


class StockMovement(models.Model):
    """Append-only history. `quantity_delta` is signed; `resulting_on_hand` is the balance after."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stock_item = models.ForeignKey(StockItem, on_delete=models.PROTECT, related_name="movements")
    movement_type = models.CharField(max_length=12, choices=MovementType.choices)
    quantity_delta = models.DecimalField(max_digits=14, decimal_places=3)
    resulting_on_hand = models.DecimalField(max_digits=14, decimal_places=3)
    reason = models.CharField(max_length=255, blank=True)
    reservation_id = models.UUIDField(null=True, blank=True)
    order_id = models.UUIDField(null=True, blank=True)
    actor_id = models.UUIDField(null=True, blank=True)  # null for system actions
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["reservation_id"], condition=Q(movement_type="sale"), name="one_sale_movement_per_reservation"
            ),
        ]


class ReservationStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    COMMITTED = "committed", "Committed"
    RELEASED = "released", "Released"
    EXPIRED = "expired", "Expired"


class Reservation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stock_item = models.ForeignKey(StockItem, on_delete=models.PROTECT, related_name="reservations")
    order_id = models.UUIDField(db_index=True)  # orders domain, by value
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    status = models.CharField(max_length=10, choices=ReservationStatus.choices, default=ReservationStatus.ACTIVE)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["order_id", "stock_item"], name="one_reservation_per_order_and_item"),
            models.CheckConstraint(condition=Q(quantity__gt=0), name="reservation_quantity_positive"),
        ]
        indexes = [models.Index(fields=["status", "expires_at"])]
