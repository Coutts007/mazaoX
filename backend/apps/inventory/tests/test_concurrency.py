"""Real concurrency against PostgreSQL: row locking must prevent overselling and double commits."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from django.db import connection

from apps.inventory import selectors, services
from core.actor import Actor
from core.errors import ConflictError

# serialized_rollback restores migration-seeded rows (categories) that a transactional flush would delete
pytestmark = pytest.mark.django_db(transaction=True, serialized_rollback=True)


def _in_thread(fn):
    def run():
        try:
            return fn()
        finally:
            connection.close()  # each thread owns its own DB connection

    return run


def _run_parallel(calls):
    with ThreadPoolExecutor(max_workers=len(calls)) as pool:
        futures = [pool.submit(_in_thread(c)) for c in calls]
    results = []
    for f in futures:
        try:
            results.append(("ok", f.result()))
        except ConflictError as exc:
            results.append(("conflict", exc))
    return results


@pytest.fixture
def stocked(make_user, make_listing):
    farmer = make_user("farmer")
    listing = make_listing(farmer)
    services.adjust_stock(Actor.from_user(farmer), listing.id, "addition", Decimal("10"))
    return listing


def test_parallel_reservations_never_oversell(stocked):
    calls = [
        (lambda: services.reserve_stock(order_id=uuid.uuid4(), listing_id=stocked.id, quantity=Decimal("1"), unit="kg"))
        for _ in range(25)
    ]
    results = _run_parallel(calls)
    assert sum(1 for kind, _ in results if kind == "ok") == 10
    assert sum(1 for kind, _ in results if kind == "conflict") == 15
    a = selectors.get_availability(stocked.id)
    assert (a.reserved, a.available) == (Decimal("10"), Decimal("0"))


def test_same_order_reserved_in_parallel_creates_one_reservation(stocked):
    order = uuid.uuid4()
    calls = [
        (lambda: services.reserve_stock(order_id=order, listing_id=stocked.id, quantity=Decimal("4"), unit="kg"))
        for _ in range(8)
    ]
    results = _run_parallel(calls)
    assert {r.id for kind, r in results if kind == "ok"} and len({r.id for kind, r in results if kind == "ok"}) == 1
    assert selectors.get_availability(stocked.id).reserved == Decimal("4")


def test_parallel_commits_reduce_stock_once(stocked):
    r = services.reserve_stock(order_id=uuid.uuid4(), listing_id=stocked.id, quantity=Decimal("6"), unit="kg")
    results = _run_parallel([(lambda: services.commit_reservation(r.id)) for _ in range(8)])
    assert all(kind == "ok" for kind, _ in results)
    assert selectors.get_availability(stocked.id).on_hand == Decimal("4.000")
