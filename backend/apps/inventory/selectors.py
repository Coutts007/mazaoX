"""Read interface of the inventory domain."""

import uuid
from dataclasses import dataclass
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import QuerySet, Sum
from django.utils import timezone

from apps.inventory.models import Reservation, ReservationStatus, StockItem, StockMovement


@dataclass(frozen=True)
class Availability:
    listing_id: uuid.UUID
    unit: str
    on_hand: Decimal
    reserved: Decimal
    available: Decimal


@dataclass(frozen=True)
class ReservationInfo:
    id: uuid.UUID
    order_id: uuid.UUID
    listing_id: uuid.UUID
    quantity: Decimal
    unit: str
    status: str
    expires_at: object


def active_reserved(item: StockItem, now=None) -> Decimal:
    """Sum of unexpired active reservations. Expired ones stop holding stock immediately."""
    now = now or timezone.now()
    total = Reservation.objects.filter(
        stock_item=item, status=ReservationStatus.ACTIVE, expires_at__gt=now
    ).aggregate(total=Sum("quantity"))["total"]
    return total or Decimal("0")


def get_stock_item(listing_id) -> StockItem | None:
    return StockItem.objects.filter(listing_id=listing_id).first()


def get_availability(listing_id, unit: str = "") -> Availability:
    """available = on_hand - active reservations. A listing with no stock record has zero."""
    item = get_stock_item(listing_id)
    if item is None:
        zero = Decimal("0.000")
        return Availability(listing_id, unit, zero, zero, zero)
    reserved = active_reserved(item)
    return Availability(listing_id, item.unit, item.on_hand, reserved, item.on_hand - reserved)


def list_movements(listing_id) -> QuerySet[StockMovement]:
    return StockMovement.objects.filter(stock_item__listing_id=listing_id)


def to_info(reservation: Reservation) -> ReservationInfo:
    item = reservation.stock_item
    return ReservationInfo(
        id=reservation.id, order_id=reservation.order_id, listing_id=item.listing_id,
        quantity=reservation.quantity, unit=item.unit, status=reservation.status, expires_at=reservation.expires_at,
    )


def get_reservation(reservation_id) -> ReservationInfo | None:
    try:
        r = Reservation.objects.select_related("stock_item").filter(pk=reservation_id).first()
    except (ValueError, ValidationError):  # malformed id
        return None
    return to_info(r) if r else None


def get_availability_bulk(listing_ids) -> dict[str, Decimal]:
    """available quantity per listing id (str) for a batch; listings without stock are absent (= 0)."""
    now = timezone.now()
    out = {}
    items = list(StockItem.objects.filter(listing_id__in=list(listing_ids)))
    reserved = {
        r["stock_item_id"]: r["total"]
        for r in Reservation.objects.filter(stock_item__in=items, status=ReservationStatus.ACTIVE, expires_at__gt=now)
        .values("stock_item_id").annotate(total=Sum("quantity"))
    }
    for item in items:
        out[str(item.listing_id)] = item.on_hand - (reserved.get(item.id) or Decimal("0"))
    return out


def listing_ids_with_min_available(minimum: Decimal):
    """Queryset of listing ids whose available quantity (on-hand minus live reservations) is at least `minimum`."""
    from django.db.models import DecimalField, F, OuterRef, Subquery, Value
    from django.db.models.functions import Coalesce

    held = (
        Reservation.objects.filter(stock_item=OuterRef("pk"), status=ReservationStatus.ACTIVE, expires_at__gt=timezone.now())
        .values("stock_item").annotate(total=Sum("quantity")).values("total")
    )
    zero = Value(Decimal("0"), output_field=DecimalField())
    return (
        StockItem.objects.annotate(held=Coalesce(Subquery(held, output_field=DecimalField()), zero))
        .annotate(free=F("on_hand") - F("held"))
        .filter(free__gte=minimum, free__gt=0)
        .values_list("listing_id", flat=True)
    )
