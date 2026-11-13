import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from django.db import connection

from apps.inventory import selectors as inv
from apps.orders import services
from apps.orders.models import Order
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


def test_many_buyers_cannot_oversell(shop):
    buyers = [shop["make_user"]("buyer") for _ in range(12)]
    item = {"listing_id": shop["tomatoes"].id, "quantity": Decimal("30"), "quantity_unit": "kg"}
    calls = [
        (lambda b=b: services.create_order(Actor.from_user(b), items=[dict(item)], delivery_method="collection"))
        for b in buyers
    ]
    results = _parallel(calls)
    assert sum(1 for k, _ in results if k == "ok") == 3  # 100 kg / 30 kg
    assert Order.objects.count() == 3
    a = inv.get_availability(shop["tomatoes"].id)
    assert (a.reserved, a.available) == (Decimal("90"), Decimal("10"))


def test_same_idempotency_key_in_parallel_creates_one_order(shop):
    item = {"listing_id": shop["tomatoes"].id, "quantity": Decimal("5"), "quantity_unit": "kg"}
    buyer = Actor.from_user(shop["buyer"])
    calls = [
        (lambda: services.create_order(buyer, items=[dict(item)], delivery_method="collection", idempotency_key="parallel-key-1"))
        for _ in range(8)
    ]
    results = _parallel(calls)
    ids = {o.id for k, (o, _) in results if k == "ok"}
    assert len(ids) == 1 and Order.objects.count() == 1
    assert inv.get_availability(shop["tomatoes"].id).reserved == Decimal("5")
