import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.inventory import selectors as inv
from apps.orders import selectors as orders
from apps.orders import services as order_services
from apps.orders.models import Order
from apps.payments import services
from core.actor import Actor
from core.errors import ConflictError, ForbiddenError, InvalidInputError, NotFoundError

pytestmark = pytest.mark.django_db
D = Decimal


def buyer(shop):
    return Actor.from_user(shop["buyer"])


def test_start_creates_attempt_with_server_amount(shop):
    order = shop["place"]("10")
    attempt, created = services.start_simulated_payment(buyer(shop), order.id)
    assert created and attempt.status == "pending" and attempt.amount == D("850.00")


def test_start_is_idempotent_while_pending(shop):
    order = shop["place"]()
    a, _ = services.start_simulated_payment(buyer(shop), order.id)
    b, created = services.start_simulated_payment(buyer(shop), order.id)
    assert a.id == b.id and not created


def test_start_authorization_and_state(shop):
    order = shop["place"]()
    with pytest.raises(ForbiddenError):
        services.start_simulated_payment(Actor.from_user(shop["farmer"]), order.id)
    with pytest.raises(NotFoundError):
        services.start_simulated_payment(Actor.from_user(shop["make_user"]("buyer")), order.id)
    with pytest.raises(NotFoundError):
        services.start_simulated_payment(buyer(shop), uuid.uuid4())
    order_services.cancel_order(buyer(shop), order.id)
    with pytest.raises(ConflictError) as e:
        services.start_simulated_payment(buyer(shop), order.id)
    assert e.value.code == "ORDER_NOT_PAYABLE"


def test_start_rejected_after_payment_window(shop):
    order = shop["place"]()
    Order.objects.filter(pk=order.id).update(created_at=timezone.now() - timedelta(minutes=30))
    with pytest.raises(ConflictError) as e:
        services.start_simulated_payment(buyer(shop), order.id)
    assert e.value.code == "PAYMENT_WINDOW_ELAPSED"


def test_success_marks_order_paid_and_commits_stock(shop):
    order = shop["place"]("10")
    attempt, _ = services.start_simulated_payment(buyer(shop), order.id)
    done = services.complete_simulated_payment(buyer(shop), attempt.id, "success")
    assert done.status == "succeeded" and done.completed_at
    paid = orders.get_order(order.id)
    assert paid.status == "paid"
    a = inv.get_availability(shop["listing"].id)
    assert (a.on_hand, a.reserved, a.available) == (D("90"), D("0"), D("90"))
    assert [h.to_status for h in paid.history.all()] == ["pending_payment", "paid"]


def test_success_is_idempotent_and_cannot_flip(shop):
    order = shop["place"]()
    attempt, _ = services.start_simulated_payment(buyer(shop), order.id)
    services.complete_simulated_payment(buyer(shop), attempt.id, "success")
    services.complete_simulated_payment(buyer(shop), attempt.id, "success")
    assert inv.get_availability(shop["listing"].id).on_hand == D("90")  # stock reduced once
    with pytest.raises(ConflictError) as e:
        services.complete_simulated_payment(buyer(shop), attempt.id, "failure")
    assert e.value.code == "PAYMENT_ALREADY_COMPLETED"


def test_failure_keeps_order_payable_and_allows_retry(shop):
    order = shop["place"]("10")
    first, _ = services.start_simulated_payment(buyer(shop), order.id)
    assert services.complete_simulated_payment(buyer(shop), first.id, "failure").status == "failed"
    assert orders.get_order(order.id).status == "pending_payment"
    assert inv.get_availability(shop["listing"].id).reserved == D("10")  # still held
    second, created = services.start_simulated_payment(buyer(shop), order.id)
    assert created and second.id != first.id
    services.complete_simulated_payment(buyer(shop), second.id, "success")
    assert orders.get_order(order.id).status == "paid"


def test_cancelled_order_fails_payment_without_touching_stock(shop):
    order = shop["place"]("10")
    attempt, _ = services.start_simulated_payment(buyer(shop), order.id)
    order_services.cancel_order(buyer(shop), order.id)
    done = services.complete_simulated_payment(buyer(shop), attempt.id, "success")
    assert done.status == "failed" and done.failure_reason == "order_not_payable"
    assert orders.get_order(order.id).status == "cancelled"
    assert inv.get_availability(shop["listing"].id).on_hand == D("100")


def test_expired_reservation_fails_payment_and_leaves_order_unpaid(shop, monkeypatch):
    order = shop["place"]("10")
    attempt, _ = services.start_simulated_payment(buyer(shop), order.id)
    later = timezone.now() + timedelta(minutes=16)  # time travel past the 15-minute reservation window
    monkeypatch.setattr("apps.inventory.services.timezone.now", lambda: later)
    done = services.complete_simulated_payment(buyer(shop), attempt.id, "success")
    assert done.status == "failed" and done.failure_reason == "reservation_expired"
    assert orders.get_order(order.id).status == "pending_payment"
    assert inv.get_availability(shop["listing"].id).on_hand == D("100")


def test_only_owner_or_admin_can_complete(shop):
    order = shop["place"]()
    attempt, _ = services.start_simulated_payment(buyer(shop), order.id)
    with pytest.raises(NotFoundError):
        services.complete_simulated_payment(Actor.from_user(shop["make_user"]("buyer")), attempt.id, "success")
    with pytest.raises(NotFoundError):
        services.complete_simulated_payment(Actor.from_user(shop["farmer"]), attempt.id, "success")
    assert services.complete_simulated_payment(Actor(uuid.uuid4(), "admin"), attempt.id, "failure").status == "failed"


def test_invalid_outcome(shop):
    order = shop["place"]()
    attempt, _ = services.start_simulated_payment(buyer(shop), order.id)
    with pytest.raises(InvalidInputError):
        services.complete_simulated_payment(buyer(shop), attempt.id, "maybe")


def test_completion_disabled_returns_not_found(shop, settings):
    order = shop["place"]()
    attempt, _ = services.start_simulated_payment(buyer(shop), order.id)
    settings.PAYMENT_SIMULATION_ENABLED = False
    with pytest.raises(NotFoundError):
        services.complete_simulated_payment(buyer(shop), attempt.id, "success")
    assert orders.get_order(order.id).status == "pending_payment"


def test_pay_cancel_after_paid_is_refused(shop):
    order = shop["place"]()
    attempt, _ = services.start_simulated_payment(buyer(shop), order.id)
    services.complete_simulated_payment(buyer(shop), attempt.id, "success")
    with pytest.raises(ConflictError):
        order_services.cancel_order(buyer(shop), order.id)
