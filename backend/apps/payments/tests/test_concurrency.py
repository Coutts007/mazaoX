from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from django.db import connection

from apps.inventory import selectors as inv
from apps.orders import selectors as orders
from apps.orders import services as order_services
from apps.payments import services
from core.actor import Actor
from core.errors import ConflictError

# serialized_rollback restores migration-seeded rows (categories) that a transactional flush would delete
pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)


def _parallel(calls):
    def wrap(fn):
        def run():
            try:
                return fn()
            finally:
                connection.close()
        return run

    with ThreadPoolExecutor(max_workers=len(calls)) as pool:
        futures = [pool.submit(wrap(c)) for c in calls]
    out = []
    for f in futures:
        try:
            out.append(("ok", f.result()))
        except ConflictError as exc:
            out.append(("conflict", exc))
    return out


def test_parallel_success_completions_reduce_stock_once(shop):
    order = shop["place"]("10")
    buyer = Actor.from_user(shop["buyer"])
    attempt, _ = services.start_simulated_payment(buyer, order.id)
    results = _parallel([(lambda: services.complete_simulated_payment(buyer, attempt.id, "success")) for _ in range(8)])
    assert all(k == "ok" and r.status == "succeeded" for k, r in results)
    assert inv.get_availability(shop["listing"].id).on_hand == Decimal("90.000")
    assert orders.get_order(order.id).status == "paid"


def test_pay_versus_cancel_race_ends_consistent(shop):
    """Whichever wins, order status, payment status and stock must agree (never paid AND released)."""
    buyer = Actor.from_user(shop["buyer"])
    for _ in range(6):
        order = shop["place"]("5")
        attempt, _ = services.start_simulated_payment(buyer, order.id)
        _parallel([
            lambda: services.complete_simulated_payment(buyer, attempt.id, "success"),
            lambda: order_services.cancel_order(buyer, order.id),
        ])
        final = orders.get_order(order.id).status
        pay = services.selectors.get_attempt(attempt.id).status
        assert (final, pay) in {("paid", "succeeded"), ("cancelled", "failed")}, (final, pay)
    a = inv.get_availability(shop["listing"].id)
    paid_count = sum(1 for o in orders.list_orders(Actor.from_user(shop["buyer"])) if o.status == "paid")
    assert a.on_hand == Decimal("100") - 5 * paid_count and a.reserved == 0
