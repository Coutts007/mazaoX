"""Read interface of the orders domain."""

import uuid
from datetime import timedelta
from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import QuerySet

from apps.orders.models import Order, OrderStatus
from core.actor import Actor


@dataclass(frozen=True)
class OrderSnapshot:
    """What other domains (payments, notifications) may know about an order."""

    id: uuid.UUID
    buyer_id: uuid.UUID
    farmer_id: uuid.UUID
    status: str
    total_amount: Decimal
    payment_due_by: object  # datetime while pending_payment, else None


def payment_due_by(order: Order):
    if order.status != OrderStatus.PENDING_PAYMENT:
        return None
    return order.created_at + timedelta(minutes=settings.RESERVATION_TTL_MINUTES)


def _participant(order: Order, actor: Actor) -> bool:
    return actor.is_admin or actor.id in (order.buyer_id, order.farmer_id)


def get_order(order_id) -> Order | None:
    try:
        return Order.objects.prefetch_related("lines").filter(pk=order_id).first()
    except (ValueError, TypeError, ValidationError):
        return None


def get_order_for_actor(order_id, actor: Actor) -> Order | None:
    """Participants and admins only. Others get None, so existence is not revealed."""
    order = get_order(order_id)
    return order if order is not None and _participant(order, actor) else None


def get_order_snapshot(order_id) -> OrderSnapshot | None:
    o = get_order(order_id)
    if o is None:
        return None
    return OrderSnapshot(o.id, o.buyer_id, o.farmer_id, o.status, o.total_amount, payment_due_by(o))


def list_orders(actor: Actor, status: str = "") -> QuerySet[Order]:
    qs = Order.objects.prefetch_related("lines")
    if actor.role == "buyer":
        qs = qs.filter(buyer_id=actor.id)
    elif actor.role == "farmer":
        qs = qs.filter(farmer_id=actor.id)
    elif not actor.is_admin:
        qs = qs.none()
    return qs.filter(status=status) if status else qs
