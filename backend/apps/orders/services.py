"""Write interface of the orders domain.

Orders coordinate; they never touch stock tables. Reservations are made and released only
through `inventory.services`. Order creation runs in ONE database transaction, so if any line
cannot be reserved the order row, its lines and every reservation made so far are rolled back.
"""

import hashlib
import json
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.catalogue import selectors as catalogue
from apps.inventory import services as inventory
from apps.orders import selectors
from apps.orders.models import DeliveryMethod, Order, OrderLine, OrderStatus, OrderStatusHistory
from core.actor import Actor
from core.errors import ConflictError, DomainError, ForbiddenError, InvalidInputError, NotFoundError

MAX_LINES = 20
CENT = Decimal("0.01")


def _record(order: Order, from_status: str, to_status: str, actor_id=None, note: str = "") -> None:
    OrderStatusHistory.objects.create(order=order, from_status=from_status, to_status=to_status, actor_id=actor_id, note=note)


def _fingerprint(items: list[dict], delivery_method: str, delivery_location: str) -> str:
    canonical = json.dumps(
        {
            "items": sorted(
                ({"l": str(i["listing_id"]), "q": str(Decimal(i["quantity"]).normalize()), "u": i["quantity_unit"]} for i in items),
                key=lambda x: x["l"],
            ),
            "m": delivery_method,
            "d": delivery_location.strip(),
        },
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _existing_for_key(buyer_id, key: str, request_hash: str) -> Order | None:
    existing = Order.objects.prefetch_related("lines").filter(buyer_id=buyer_id, idempotency_key=key).first()
    if existing is None:
        return None
    if existing.request_hash != request_hash:
        raise ConflictError("This Idempotency-Key was already used with a different request.", code="IDEMPOTENCY_CONFLICT")
    return existing


def create_order(
    actor: Actor, *, items: list[dict], delivery_method: str, delivery_location: str = "", idempotency_key: str | None = None
) -> tuple[Order, bool]:
    """Create an order and reserve stock. Returns (order, created); created=False on idempotent replay."""
    if actor.role != "buyer":
        raise ForbiddenError("Only buyers can place orders.")
    if not items or len(items) > MAX_LINES:
        raise InvalidInputError(f"An order needs between 1 and {MAX_LINES} items.", "items")
    if delivery_method not in DeliveryMethod.values:
        raise InvalidInputError("Delivery method must be collection or delivery.", "delivery_method")
    delivery_location = (delivery_location or "").strip()
    if delivery_method == DeliveryMethod.DELIVERY and not delivery_location:
        raise InvalidInputError("A delivery location is required for delivery.", "delivery_location")
    ids = [str(i["listing_id"]) for i in items]
    if len(set(ids)) != len(ids):
        raise InvalidInputError("Each listing can appear only once per order.", "items")

    request_hash = _fingerprint(items, delivery_method, delivery_location)
    if idempotency_key:
        replay = _existing_for_key(actor.id, idempotency_key, request_hash)
        if replay is not None:
            return replay, False

    # Prices and totals come from the catalogue, never from the client.
    resolved = []
    for index, item in enumerate(items):
        listing = catalogue.get_listing_snapshot(item["listing_id"])
        if listing is None or not listing.is_active:
            raise InvalidInputError("This listing is not available.", f"items.{index}.listing_id")
        if item["quantity"] <= 0:
            raise InvalidInputError("Quantity must be greater than zero.", f"items.{index}.quantity")
        if item["quantity_unit"] != listing.quantity_unit:
            raise InvalidInputError(f"Quantity unit must be {listing.quantity_unit}.", f"items.{index}.quantity_unit")
        resolved.append((index, item["quantity"], listing))
    if len({listing.farmer_id for _, _, listing in resolved}) != 1:
        raise InvalidInputError("One order can only contain produce from one farmer.", "items")
    farmer_id = resolved[0][2].farmer_id
    if farmer_id == actor.id:
        raise InvalidInputError("You cannot order your own produce.", "items")

    line_totals = [(q * l.price_per_unit).quantize(CENT, ROUND_HALF_UP) for _, q, l in resolved]
    total = sum(line_totals, Decimal("0.00"))

    try:
        with transaction.atomic():
            order = Order.objects.create(
                buyer_id=actor.id, farmer_id=farmer_id, delivery_method=delivery_method,
                delivery_location=delivery_location, total_amount=total,
                idempotency_key=idempotency_key or None, request_hash=request_hash,
            )
            for (index, quantity, listing), line_total in zip(resolved, line_totals):
                try:
                    reservation = inventory.reserve_stock(
                        order_id=order.id, listing_id=listing.id, quantity=quantity, unit=listing.quantity_unit
                    )
                except NotFoundError as exc:
                    raise InvalidInputError(exc.message, f"items.{index}.listing_id") from exc
                except DomainError as exc:  # e.g. INSUFFICIENT_STOCK: re-point the error at the failing line
                    raise type(exc)(exc.message, f"items.{index}.{exc.field or 'quantity'}", exc.code) from exc
                OrderLine.objects.create(
                    order=order, listing_id=listing.id, produce_name=listing.produce_name, unit_price=listing.price_per_unit,
                    quantity=quantity, quantity_unit=listing.quantity_unit, line_total=line_total, reservation_id=reservation.id,
                )
            _record(order, "", OrderStatus.PENDING_PAYMENT, actor.id, "Order placed")
    except IntegrityError:
        # Concurrent request with the same idempotency key won the race: return its order.
        if idempotency_key:
            replay = _existing_for_key(actor.id, idempotency_key, request_hash)
            if replay is not None:
                return replay, False
        raise
    return selectors.get_order(order.id), True


def _release_all(order: Order) -> None:
    for line in order.lines.all():
        inventory.release_reservation(line.reservation_id)


@transaction.atomic
def cancel_order(actor: Actor, order_id, reason: str = "") -> Order:
    """Cancel an unpaid order and release its stock. Idempotent. Paid orders need the refund flow (later sprint)."""
    visible = selectors.get_order_for_actor(order_id, actor)
    if visible is None:
        raise NotFoundError("Order not found.")
    order = Order.objects.select_for_update().get(pk=visible.pk)
    if order.status == OrderStatus.CANCELLED:
        return selectors.get_order(order.id)
    if order.status != OrderStatus.PENDING_PAYMENT:
        raise ConflictError(f"A {order.get_status_display().lower()} order cannot be cancelled.", code="ORDER_NOT_CANCELLABLE")
    _release_all(order)
    previous, order.status = order.status, OrderStatus.CANCELLED
    order.save(update_fields=["status", "updated_at"])
    _record(order, previous, order.status, actor.id, (reason or "").strip()[:255])
    return selectors.get_order(order.id)


def expire_unpaid_orders(now=None) -> int:
    """System sweep: unpaid orders older than the reservation window become `expired` and free their stock."""
    now = now or timezone.now()
    cutoff = now - timedelta(minutes=settings.RESERVATION_TTL_MINUTES)
    count = 0
    for order_id in list(
        Order.objects.filter(status=OrderStatus.PENDING_PAYMENT, created_at__lte=cutoff).values_list("pk", flat=True)
    ):
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=order_id)
            if order.status != OrderStatus.PENDING_PAYMENT:
                continue  # paid or cancelled while we were sweeping
            _release_all(order)
            order.status = OrderStatus.EXPIRED
            order.save(update_fields=["status", "updated_at"])
            _record(order, OrderStatus.PENDING_PAYMENT, OrderStatus.EXPIRED, None, "Payment window elapsed")
            count += 1
    return count
