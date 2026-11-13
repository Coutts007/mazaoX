import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.catalogue import services as catalogue_services
from apps.inventory import selectors, services
from apps.inventory.models import Reservation, StockMovement
from core.actor import Actor
from core.errors import ConflictError, ForbiddenError, InvalidInputError, NotFoundError

pytestmark = pytest.mark.django_db
D = Decimal


@pytest.fixture
def setup(make_user, make_listing):
    farmer = make_user("farmer")
    listing = make_listing(farmer)
    return farmer, listing, Actor.from_user(farmer)


def stock(actor, listing, qty="100", kind="addition", reason=""):
    return services.adjust_stock(actor, listing.id, kind, D(qty), reason)


def reserve(listing, qty="10", order=None):
    return services.reserve_stock(order_id=order or uuid.uuid4(), listing_id=listing.id, quantity=D(qty), unit="kg")


def test_no_stock_record_means_zero_available(setup):
    _, listing, _ = setup
    assert selectors.get_availability(listing.id, "kg").available == 0


def test_addition_creates_stock_and_movement(setup):
    _, listing, actor = setup
    m = stock(actor, listing, "50.5")
    assert m.resulting_on_hand == D("50.500") and m.quantity_delta == D("50.500")
    assert selectors.get_availability(listing.id).available == D("50.500")


def test_spoilage_and_correction_need_reason(setup):
    _, listing, actor = setup
    stock(actor, listing, "100")
    for kind in ("spoilage", "correction"):
        with pytest.raises(InvalidInputError) as e:
            stock(actor, listing, "5", kind)
        assert e.value.field == "reason"
    stock(actor, listing, "10", "spoilage", "Rotted in transit")
    stock(actor, listing, "-5", "correction", "Recount")
    assert selectors.get_availability(listing.id).on_hand == D("85.000")


@pytest.mark.parametrize("kind,qty", [("addition", "0"), ("addition", "-1"), ("spoilage", "-1"), ("sale", "1"), ("bogus", "1")])
def test_invalid_adjustments(setup, kind, qty):
    _, listing, actor = setup
    with pytest.raises(InvalidInputError):
        stock(actor, listing, qty, kind, "r")


def test_cannot_go_negative(setup):
    _, listing, actor = setup
    stock(actor, listing, "10")
    with pytest.raises(ConflictError):
        stock(actor, listing, "11", "spoilage", "loss")
    assert selectors.get_availability(listing.id).on_hand == D("10.000")


def test_cannot_drop_below_reserved(setup):
    _, listing, actor = setup
    stock(actor, listing, "10")
    reserve(listing, "8")
    with pytest.raises(ConflictError) as e:
        stock(actor, listing, "5", "spoilage", "loss")
    assert e.value.code == "INSUFFICIENT_STOCK"
    stock(actor, listing, "2", "spoilage", "loss")  # exactly down to the reserved amount


def test_only_owner_can_adjust(setup, make_user):
    _, listing, _ = setup
    other = Actor.from_user(make_user("farmer"))
    with pytest.raises(ForbiddenError):
        stock(other, listing)
    with pytest.raises(ForbiddenError):  # admins do not edit stock
        stock(Actor(uuid.uuid4(), "admin"), listing)
    with pytest.raises(NotFoundError):
        services.adjust_stock(other, uuid.uuid4(), "addition", D(1))


def test_reserve_reduces_availability_not_on_hand(setup):
    _, listing, actor = setup
    stock(actor, listing, "100")
    r = reserve(listing, "30")
    a = selectors.get_availability(listing.id)
    assert (a.on_hand, a.reserved, a.available) == (D("100"), D("30"), D("70"))
    assert r.status == "active" and r.expires_at > timezone.now()


def test_reserve_insufficient_stock(setup):
    _, listing, actor = setup
    stock(actor, listing, "10")
    with pytest.raises(ConflictError) as e:
        reserve(listing, "10.001")
    assert e.value.code == "INSUFFICIENT_STOCK"
    with pytest.raises(ConflictError):
        reserve(listing, "11")


def test_reserve_validates_input(setup):
    _, listing, actor = setup
    stock(actor, listing, "10")
    with pytest.raises(InvalidInputError):
        reserve(listing, "0")
    with pytest.raises(InvalidInputError):
        services.reserve_stock(order_id=uuid.uuid4(), listing_id=listing.id, quantity=D(1), unit="bag")
    with pytest.raises(NotFoundError):
        services.reserve_stock(order_id=uuid.uuid4(), listing_id=uuid.uuid4(), quantity=D(1), unit="kg")


def test_reserve_inactive_listing_rejected(setup):
    farmer, listing, actor = setup
    stock(actor, listing, "10")
    catalogue_services.deactivate_listing(actor, listing.id)
    with pytest.raises(NotFoundError):
        reserve(listing, "1")


def test_reserve_is_idempotent_per_order(setup):
    _, listing, actor = setup
    stock(actor, listing, "10")
    order = uuid.uuid4()
    first, second = reserve(listing, "4", order), reserve(listing, "4", order)
    assert first.id == second.id
    assert selectors.get_availability(listing.id).reserved == D("4")
    with pytest.raises(ConflictError):
        reserve(listing, "5", order)


def test_commit_reduces_on_hand_once(setup):
    _, listing, actor = setup
    stock(actor, listing, "10")
    r = reserve(listing, "4")
    services.commit_reservation(r.id)
    services.commit_reservation(r.id)  # retry
    a = selectors.get_availability(listing.id)
    assert (a.on_hand, a.reserved, a.available) == (D("6"), D("0"), D("6"))
    sales = StockMovement.objects.filter(movement_type="sale")
    assert sales.count() == 1 and sales[0].quantity_delta == D("-4.000")


def test_release_returns_stock_without_touching_on_hand(setup):
    _, listing, actor = setup
    stock(actor, listing, "10")
    r = reserve(listing, "4")
    services.release_reservation(r.id)
    services.release_reservation(r.id)
    a = selectors.get_availability(listing.id)
    assert (a.on_hand, a.available) == (D("10"), D("10"))
    with pytest.raises(ConflictError):
        services.commit_reservation(r.id)


def test_cannot_release_committed(setup):
    _, listing, actor = setup
    stock(actor, listing, "10")
    r = reserve(listing, "4")
    services.commit_reservation(r.id)
    with pytest.raises(ConflictError):
        services.release_reservation(r.id)


def test_expired_reservation_stops_holding_stock_and_cannot_commit(setup):
    _, listing, actor = setup
    stock(actor, listing, "10")
    r = reserve(listing, "10")
    Reservation.objects.filter(pk=r.id).update(expires_at=timezone.now() - timedelta(seconds=1))
    assert selectors.get_availability(listing.id).available == D("10")  # before any sweep
    with pytest.raises(ConflictError) as e:
        services.commit_reservation(r.id)
    assert e.value.code == "RESERVATION_EXPIRED"
    assert selectors.get_availability(listing.id).on_hand == D("10")


def test_expire_sweep(setup):
    _, listing, actor = setup
    stock(actor, listing, "10")
    old, fresh = reserve(listing, "3"), reserve(listing, "2")
    Reservation.objects.filter(pk=old.id).update(expires_at=timezone.now() - timedelta(minutes=1))
    assert services.expire_reservations() == 1
    assert services.expire_reservations() == 0
    assert selectors.get_reservation(old.id).status == "expired"
    assert selectors.get_reservation(fresh.id).status == "active"
    with pytest.raises(ConflictError):
        services.commit_reservation(old.id)
    services.release_reservation(old.id)  # idempotent on expired


def test_unknown_reservation(setup):
    for bad in (uuid.uuid4(), "garbage"):
        with pytest.raises(NotFoundError):
            services.commit_reservation(bad)
    assert selectors.get_reservation("garbage") is None
