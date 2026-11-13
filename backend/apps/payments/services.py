"""Write interface of the payments domain (SIMULATION ONLY).

Success is decided here, on the server, after the order service confirms the order and commits
stock. Nothing the browser sends can mark an order paid. No payment credentials are accepted.
"""

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.orders import selectors as orders
from apps.orders import services as order_services
from apps.payments import selectors
from apps.payments.models import PaymentAttempt, PaymentStatus
from core.actor import Actor
from core.errors import ConflictError, DomainError, ForbiddenError, InvalidInputError, NotFoundError

OUTCOMES = {"success", "failure"}


def _require_simulation_enabled() -> None:
    if not settings.PAYMENT_SIMULATION_ENABLED:
        raise NotFoundError("Not found.")  # indistinguishable from a missing route when disabled


def start_simulated_payment(actor: Actor, order_id) -> tuple[PaymentAttempt, bool]:
    """Create (or return the existing open) attempt for an order. Returns (attempt, created)."""
    if actor.role != "buyer":
        raise ForbiddenError("Only the buyer can pay for an order.")
    order = orders.get_order_snapshot(order_id)
    if order is None or order.buyer_id != actor.id:
        raise NotFoundError("Order not found.")
    if order.status != "pending_payment":
        raise ConflictError(f"This order is {order.status.replace('_', ' ')} and cannot be paid.", code="ORDER_NOT_PAYABLE")
    if order.payment_due_by <= timezone.now():
        raise ConflictError("The payment window for this order has elapsed.", code="PAYMENT_WINDOW_ELAPSED")
    existing = selectors.pending_attempt_for_order(order.id)
    if existing is not None:
        return existing, False
    try:
        with transaction.atomic():
            return PaymentAttempt.objects.create(order_id=order.id, buyer_id=actor.id, amount=order.total_amount), True
    except IntegrityError:  # a concurrent request opened the attempt first
        existing = selectors.pending_attempt_for_order(order.id)
        if existing is None:
            raise
        return existing, False


def complete_simulated_payment(actor: Actor, payment_id, outcome: str) -> PaymentAttempt:
    """Demo-only: set the simulated outcome. Idempotent for the same outcome; conflicting repeats get 409."""
    _require_simulation_enabled()
    if outcome not in OUTCOMES:
        raise InvalidInputError("Outcome must be success or failure.", "outcome")
    visible = selectors.get_attempt_for_actor(payment_id, actor)
    if visible is None:
        raise NotFoundError("Payment not found.")

    with transaction.atomic():
        attempt = PaymentAttempt.objects.select_for_update().get(pk=visible.pk)
        wanted = PaymentStatus.SUCCEEDED if outcome == "success" else PaymentStatus.FAILED
        if attempt.status != PaymentStatus.PENDING:
            if attempt.status == wanted:
                return attempt
            raise ConflictError(f"This payment is already {attempt.status}.", code="PAYMENT_ALREADY_COMPLETED")

        if outcome == "failure":
            return _finish(attempt, PaymentStatus.FAILED, "simulated_failure")

        order = orders.get_order_snapshot(attempt.order_id)
        if order is None or order.total_amount != attempt.amount:
            return _finish(attempt, PaymentStatus.FAILED, "amount_mismatch")
        try:
            with transaction.atomic():  # savepoint: a failed confirmation changes nothing in orders/inventory
                order_services.confirm_payment(attempt.order_id, reference=f"(payment {attempt.id})")
        except DomainError as exc:
            return _finish(attempt, PaymentStatus.FAILED, (exc.code or "order_not_payable").lower()[:40])
        return _finish(attempt, PaymentStatus.SUCCEEDED, "")


def _finish(attempt: PaymentAttempt, status: str, reason: str) -> PaymentAttempt:
    attempt.status = status
    attempt.failure_reason = reason
    attempt.completed_at = timezone.now()
    attempt.save(update_fields=["status", "failure_reason", "completed_at"])
    return attempt
