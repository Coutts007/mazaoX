from django.core.exceptions import ValidationError
from django.db.models import QuerySet

from apps.payments.models import PaymentAttempt
from core.actor import Actor


def get_attempt(payment_id) -> PaymentAttempt | None:
    try:
        return PaymentAttempt.objects.filter(pk=payment_id).first()
    except (ValueError, TypeError, ValidationError):
        return None


def get_attempt_for_actor(payment_id, actor: Actor) -> PaymentAttempt | None:
    """Owner (buyer) or admin only; others get None so existence is not revealed."""
    attempt = get_attempt(payment_id)
    if attempt is None or not (actor.is_admin or attempt.buyer_id == actor.id):
        return None
    return attempt


def pending_attempt_for_order(order_id) -> PaymentAttempt | None:
    return PaymentAttempt.objects.filter(order_id=order_id, status="pending").first()


def list_attempts_for_order(order_id) -> QuerySet[PaymentAttempt]:
    return PaymentAttempt.objects.filter(order_id=order_id)
