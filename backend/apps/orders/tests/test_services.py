import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.inventory import selectors as inv
from apps.orders import selectors, services
from apps.orders.models import Order, OrderStatus
from core.actor import Actor
from core.errors import ConflictError, ForbiddenError, InvalidInputError, NotFoundError

pytestmark = pytest.mark.django_db
D = Decimal


def item(listing, qty="10", unit="kg"):
    return {"listing_id": listing.id, "quantity": D(qty), "quantity_unit": unit}


def place(shop, *items, key=None, method="collection", location="", buyer=None):
    return services.create_order(
        Actor.from_user(buyer or shop["buyer"]), items=list(items), delivery_method=method,
        delivery_location=location, idempotency_key=key,
    )


def test_create_order_calculates_totals_and_reserves_stock(shop):
    order, created = place(shop, item(shop["tomatoes"], "10"), item(shop["onions"], "3.5"))
    assert created and order.status == OrderStatus.PENDING_PAYMENT
    assert order.total_amount == D("850.00") + D("211.75")
    lines = {l.produce_name: l for l in order.lines.all()}
    assert lines["Tomatoes"].unit_price == D("85.00") and lines["Tomatoes"].line_total == D("850.00")
    assert inv.get_availability(shop["tomatoes"].id).available == D("90")
    assert inv.get_availability(shop["onions"].id).available == D("46.5")
    assert [h.to_status for h in order.history.all()] == ["pending_payment"]


def test_snapshot_survives_later_price_change(shop):
    from apps.catalogue import services as cat

    order, _ = place(shop, item(shop["tomatoes"], "2"))
    cat.update_listing(shop["farmer_actor"], shop["tomatoes"].id, {"price_per_unit": D("999.00")})
    assert selectors.get_order(order.id).lines.get().unit_price == D("85.00")


def test_rounding_half_up(shop):
    cheap = shop["make_listing"](shop["farmer"], price_per_unit="0.05")
    from apps.inventory import services as i
    i.adjust_stock(shop["farmer_actor"], cheap.id, "addition", D("100"))
    order, _ = place(shop, item(cheap, "0.5"))  # 0.025 -> 0.03
    assert order.total_amount == D("0.03")


def test_only_buyers_can_order(shop):
    with pytest.raises(ForbiddenError):
        place(shop, item(shop["tomatoes"]), buyer=shop["farmer"])


@pytest.mark.parametrize(
    "mutate,field",
    [
        (lambda s: dict(items=[], method="collection"), "items"),
        (lambda s: dict(items=[item(s["tomatoes"], "0")], method="collection"), "items.0.quantity"),
        (lambda s: dict(items=[item(s["tomatoes"], "1", "bag")], method="collection"), "items.0.quantity_unit"),
        (lambda s: dict(items=[item(s["tomatoes"]), item(s["tomatoes"])], method="collection"), "items"),
        (lambda s: dict(items=[item(s["tomatoes"])], method="delivery"), "delivery_location"),
        (lambda s: dict(items=[item(s["tomatoes"])], method="drone"), "delivery_method"),
    ],
)
def test_validation(shop, mutate, field):
    args = mutate(shop)
    with pytest.raises(InvalidInputError) as e:
        place(shop, *args["items"], method=args["method"])
    assert e.value.field == field


def test_unknown_and_inactive_listing(shop):
    ghost = type("L", (), {"id": uuid.uuid4()})()
    with pytest.raises(InvalidInputError) as e:
        place(shop, item(ghost))
    assert e.value.field == "items.0.listing_id"
    from apps.catalogue import services as cat
    cat.deactivate_listing(shop["farmer_actor"], shop["tomatoes"].id)
    with pytest.raises(InvalidInputError):
        place(shop, item(shop["tomatoes"]))


def test_one_farmer_per_order(shop):
    other = shop["make_user"]("farmer")
    theirs = shop["make_listing"](other)
    with pytest.raises(InvalidInputError) as e:
        place(shop, item(shop["tomatoes"]), item(theirs))
    assert "one farmer" in e.value.message


def test_insufficient_stock_rolls_back_everything(shop):
    with pytest.raises(ConflictError) as e:
        place(shop, item(shop["tomatoes"], "10"), item(shop["onions"], "51"))
    assert e.value.code == "INSUFFICIENT_STOCK" and e.value.field == "items.1.quantity"
    assert Order.objects.count() == 0
    for key in ("tomatoes", "onions"):  # the first line's reservation was rolled back too
        a = inv.get_availability(shop[key].id)
        assert a.reserved == 0 and a.available == a.on_hand


def test_cannot_oversell_across_orders(shop):
    place(shop, item(shop["tomatoes"], "100"))
    with pytest.raises(ConflictError):
        place(shop, item(shop["tomatoes"], "1"), buyer=shop["make_user"]("buyer"))


def test_idempotent_replay_returns_original(shop):
    first, created1 = place(shop, item(shop["tomatoes"], "5"), key="key-12345678")
    second, created2 = place(shop, item(shop["tomatoes"], "5"), key="key-12345678")
    assert created1 and not created2 and first.id == second.id
    assert Order.objects.count() == 1
    assert inv.get_availability(shop["tomatoes"].id).available == D("95")


def test_same_key_different_body_conflicts(shop):
    place(shop, item(shop["tomatoes"], "5"), key="key-12345678")
    with pytest.raises(ConflictError) as e:
        place(shop, item(shop["tomatoes"], "6"), key="key-12345678")
    assert e.value.code == "IDEMPOTENCY_CONFLICT"


def test_key_is_scoped_to_buyer(shop):
    place(shop, item(shop["tomatoes"], "1"), key="key-12345678")
    other, created = place(shop, item(shop["tomatoes"], "1"), key="key-12345678", buyer=shop["make_user"]("buyer"))
    assert created


def test_cancel_releases_stock_and_is_idempotent(shop):
    order, _ = place(shop, item(shop["tomatoes"], "10"))
    buyer = Actor.from_user(shop["buyer"])
    cancelled = services.cancel_order(buyer, order.id, "Changed my mind")
    services.cancel_order(buyer, order.id)
    assert cancelled.status == OrderStatus.CANCELLED
    assert inv.get_availability(shop["tomatoes"].id).available == D("100")
    assert [h.to_status for h in selectors.get_order(order.id).history.all()] == ["pending_payment", "cancelled"]


def test_farmer_and_admin_may_cancel_strangers_may_not(shop):
    o1, _ = place(shop, item(shop["tomatoes"], "1"))
    assert services.cancel_order(Actor.from_user(shop["farmer"]), o1.id).status == "cancelled"
    o2, _ = place(shop, item(shop["tomatoes"], "1"))
    assert services.cancel_order(Actor(uuid.uuid4(), "admin"), o2.id).status == "cancelled"
    o3, _ = place(shop, item(shop["tomatoes"], "1"))
    with pytest.raises(NotFoundError):
        services.cancel_order(Actor.from_user(shop["make_user"]("buyer")), o3.id)


def test_paid_order_cannot_be_cancelled(shop):
    order, _ = place(shop, item(shop["tomatoes"], "1"))
    Order.objects.filter(pk=order.id).update(status=OrderStatus.PAID)
    with pytest.raises(ConflictError) as e:
        services.cancel_order(Actor.from_user(shop["buyer"]), order.id)
    assert e.value.code == "ORDER_NOT_CANCELLABLE"


def test_expiry_sweep_expires_old_unpaid_orders_only(shop):
    old, _ = place(shop, item(shop["tomatoes"], "10"))
    fresh, _ = place(shop, item(shop["tomatoes"], "5"))
    paid, _ = place(shop, item(shop["tomatoes"], "1"))
    Order.objects.filter(pk__in=[old.id, paid.id]).update(created_at=timezone.now() - timedelta(minutes=30))
    Order.objects.filter(pk=paid.id).update(status=OrderStatus.PAID)
    assert services.expire_unpaid_orders() == 1
    assert services.expire_unpaid_orders() == 0
    assert selectors.get_order(old.id).status == "expired"
    assert selectors.get_order(fresh.id).status == "pending_payment"
    assert inv.get_availability(shop["tomatoes"].id).available == D("100") - 5 - 1


def test_list_scoping(shop):
    mine, _ = place(shop, item(shop["tomatoes"], "1"))
    other_buyer = shop["make_user"]("buyer")
    place(shop, item(shop["tomatoes"], "1"), buyer=other_buyer)
    assert [o.id for o in selectors.list_orders(Actor.from_user(shop["buyer"]))] == [mine.id]
    assert selectors.list_orders(Actor.from_user(shop["farmer"])).count() == 2
    assert selectors.list_orders(Actor(uuid.uuid4(), "admin")).count() == 2
    other_farmer = shop["make_user"]("farmer")
    assert selectors.list_orders(Actor.from_user(other_farmer)).count() == 0
