from django.core.exceptions import ValidationError

from apps.delivery.models import Delivery
from core.actor import Actor


def get_delivery_for_order(order_id) -> Delivery | None:
    return Delivery.objects.prefetch_related("events").filter(order_id=order_id).first()


def get_delivery(delivery_id) -> Delivery | None:
    try:
        return Delivery.objects.prefetch_related("events").filter(pk=delivery_id).first()
    except (ValueError, TypeError, ValidationError):
        return None


def can_view(delivery: Delivery, actor: Actor) -> bool:
    return actor.is_admin or actor.id in (delivery.buyer_id, delivery.farmer_id)


def stats() -> dict:
    from django.db.models import Count

    return {"by_status": {r["status"]: r["n"] for r in Delivery.objects.values("status").annotate(n=Count("id"))}}

# Public contract of this module: the only names other domains may use (enforced by core/tests/test_boundaries.py).
__all__ = ['stats']
