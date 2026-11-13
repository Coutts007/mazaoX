"""Write interface of the inventory domain.

Locking order is always: StockItem row first, then Reservation row. All stock mutations happen
inside `transaction.atomic()` while holding the StockItem row lock, so concurrent reservations
for one listing are serialised and overselling is impossible.
"""

from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.catalogue import selectors as catalogue
from apps.inventory import selectors
from apps.inventory.models import (
    MovementType, Reservation, ReservationStatus, StockItem, StockMovement,
)
from core.actor import Actor
from core.errors import ConflictError, ForbiddenError, InvalidInputError, NotFoundError

ZERO = Decimal("0")
INSUFFICIENT_STOCK = "INSUFFICIENT_STOCK"


def _listing_for_owner(actor: Actor, listing_id):
    listing = catalogue.get_listing_snapshot(listing_id)
    if listing is None:
        raise NotFoundError("Listing not found.")
    if actor.id != listing.farmer_id:
        raise ForbiddenError("You can only manage stock for your own listings.")
    return listing


def _locked_item_for_listing(listing) -> StockItem:
    """Return the stock record locked FOR UPDATE, creating it on first use."""
    StockItem.objects.get_or_create(
        listing_id=listing.id, defaults={"farmer_id": listing.farmer_id, "unit": listing.quantity_unit}
    )
    return StockItem.objects.select_for_update().get(listing_id=listing.id)


@transaction.atomic
def adjust_stock(actor: Actor, listing_id, movement_type: str, quantity: Decimal, reason: str = "") -> StockMovement:
    """Owner-recorded stock change. addition/spoilage take a positive quantity; correction is signed."""
    reason = (reason or "").strip()
    if movement_type not in {MovementType.ADDITION, MovementType.CORRECTION, MovementType.SPOILAGE}:
        raise InvalidInputError("Movement type must be addition, correction or spoilage.", "movement_type")
    if quantity == 0:
        raise InvalidInputError("Quantity cannot be zero.", "quantity")
    if movement_type in {MovementType.ADDITION, MovementType.SPOILAGE} and quantity < 0:
        raise InvalidInputError("Quantity must be greater than zero.", "quantity")
    if movement_type in {MovementType.CORRECTION, MovementType.SPOILAGE} and not reason:
        raise InvalidInputError("A reason is required for this movement.", "reason")

    listing = _listing_for_owner(actor, listing_id)
    item = _locked_item_for_listing(listing)
    delta = -quantity if movement_type == MovementType.SPOILAGE else quantity
    new_on_hand = item.on_hand + delta
    reserved = selectors.active_reserved(item)
    if new_on_hand < reserved:
        raise ConflictError(
            "Stock cannot fall below quantity already reserved by open orders.", "quantity", INSUFFICIENT_STOCK
        )
    item.on_hand = new_on_hand
    item.save(update_fields=["on_hand", "updated_at"])
    return StockMovement.objects.create(
        stock_item=item, movement_type=movement_type, quantity_delta=delta,
        resulting_on_hand=new_on_hand, reason=reason, actor_id=actor.id,
    )


@transaction.atomic
def reserve_stock(*, order_id, listing_id, quantity: Decimal, unit: str) -> selectors.ReservationInfo:
    """Hold stock for an order for RESERVATION_TTL_MINUTES. Idempotent per (order, listing)."""
    if quantity <= 0:
        raise InvalidInputError("Quantity must be greater than zero.", "quantity")
    listing = catalogue.get_listing_snapshot(listing_id)
    if listing is None or not listing.is_active:
        raise NotFoundError("Listing is not available.")
    if unit != listing.quantity_unit:
        raise InvalidInputError(f"Quantity unit must be {listing.quantity_unit}.", "quantity_unit")

    item = _locked_item_for_listing(listing)
    existing = Reservation.objects.filter(stock_item=item, order_id=order_id).first()
    if existing is not None:
        if existing.quantity != quantity:
            raise ConflictError("A reservation for this order and listing already exists.", "quantity")
        return selectors.to_info(existing)

    available = item.on_hand - selectors.active_reserved(item)
    if quantity > available:
        raise ConflictError(
            f"Only {available.normalize():f} {item.unit} available.", "quantity", INSUFFICIENT_STOCK
        )
    reservation = Reservation.objects.create(
        stock_item=item, order_id=order_id, quantity=quantity,
        expires_at=timezone.now() + timedelta(minutes=settings.RESERVATION_TTL_MINUTES),
    )
    return selectors.to_info(reservation)


def _lock(reservation_id) -> tuple[StockItem, Reservation]:
    try:
        stock_item_id = Reservation.objects.values_list("stock_item_id", flat=True).get(pk=reservation_id)
    except (Reservation.DoesNotExist, ValueError, ValidationError) as exc:  # unknown or malformed id
        raise NotFoundError("Reservation not found.") from exc
    item = StockItem.objects.select_for_update().get(pk=stock_item_id)
    return item, Reservation.objects.select_for_update().get(pk=reservation_id)


@transaction.atomic
def commit_reservation(reservation_id) -> selectors.ReservationInfo:
    """Turn a reservation into a sale: on-hand drops exactly once. Idempotent."""
    item, reservation = _lock(reservation_id)
    if reservation.status == ReservationStatus.COMMITTED:
        return selectors.to_info(reservation)
    if reservation.status != ReservationStatus.ACTIVE:
        raise ConflictError(f"Reservation is {reservation.status}.", code="RESERVATION_NOT_ACTIVE")
    now = timezone.now()
    if reservation.expires_at <= now:
        raise ConflictError("Reservation has expired.", code="RESERVATION_EXPIRED")
    item.on_hand -= reservation.quantity  # DB check constraint also forbids going negative
    item.save(update_fields=["on_hand", "updated_at"])
    StockMovement.objects.create(
        stock_item=item, movement_type=MovementType.SALE, quantity_delta=-reservation.quantity,
        resulting_on_hand=item.on_hand, reservation_id=reservation.id, order_id=reservation.order_id,
    )
    reservation.status = ReservationStatus.COMMITTED
    reservation.resolved_at = now
    reservation.save(update_fields=["status", "resolved_at"])
    return selectors.to_info(reservation)


@transaction.atomic
def release_reservation(reservation_id) -> selectors.ReservationInfo:
    """Give held stock back (order failed or cancelled). Idempotent; never touches on-hand."""
    _, reservation = _lock(reservation_id)
    if reservation.status == ReservationStatus.COMMITTED:
        raise ConflictError("A committed reservation cannot be released.", code="RESERVATION_COMMITTED")
    if reservation.status == ReservationStatus.ACTIVE:
        reservation.status = ReservationStatus.RELEASED
        reservation.resolved_at = timezone.now()
        reservation.save(update_fields=["status", "resolved_at"])
    return selectors.to_info(reservation)


def expire_reservations(now=None) -> int:
    """Mark overdue active reservations expired. Safe to run repeatedly or concurrently."""
    now = now or timezone.now()
    return Reservation.objects.filter(status=ReservationStatus.ACTIVE, expires_at__lte=now).update(
        status=ReservationStatus.EXPIRED, resolved_at=now
    )
