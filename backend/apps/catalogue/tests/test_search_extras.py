from decimal import Decimal

import pytest

from apps.inventory import services as inventory
from core.actor import Actor

pytestmark = pytest.mark.django_db
URL = "/api/v1/listings"


def test_activate_flow_and_permissions(market):
    lid = market.listing.id
    farmer = market.client(market.farmer)
    farmer.post(f"{URL}/{lid}/deactivate")
    assert market.client(market.make_user("farmer")).post(f"{URL}/{lid}/activate").status_code == 404  # invisible to others
    assert market.client().post(f"{URL}/{lid}/activate").status_code == 401
    r = farmer.post(f"{URL}/{lid}/activate")
    assert r.status_code == 200 and r.json()["data"]["status"] == "active"
    assert farmer.post(f"{URL}/{lid}/activate").status_code == 200  # idempotent
    assert market.client().get(f"{URL}/{lid}").status_code == 200


def test_activate_does_not_bypass_admin_hide(market):
    lid = market.listing.id
    market.client(market.admin).patch(f"/api/v1/admin/listings/{lid}/moderation", {"hidden": True, "reason": "x"}, format="json")
    market.client(market.farmer).post(f"{URL}/{lid}/deactivate")
    market.client(market.farmer).post(f"{URL}/{lid}/activate")
    assert market.client().get(f"{URL}/{lid}").status_code == 404


def test_listing_results_include_availability(market):
    item = market.client().get(URL).json()["data"][0]
    assert item["availability"] == {"available": "1000.000", "in_stock": True}
    detail = market.client().get(f"{URL}/{market.listing.id}").json()["data"]
    assert detail["availability"]["in_stock"] is True and detail["images"] == []


def _second(market, stock, **kw):
    farmer = market.make_user("farmer")
    listing = market.make_listing(farmer, **kw)
    if stock:
        inventory.adjust_stock(Actor.from_user(farmer), listing.id, "addition", Decimal(stock))
    return listing


def test_min_quantity_filter_counts_available_not_on_hand(market):
    small = _second(market, "5", produce_name="Small")
    _second(market, None, produce_name="NoStock")
    ids = lambda **p: {i["produce_name"] for i in market.client().get(URL, p).json()["data"]}  # noqa: E731
    assert ids(min_quantity="1") == {"Tomatoes", "Small"}
    assert ids(min_quantity="500") == {"Tomatoes"}
    assert ids(min_quantity="5000") == set()
    # a live reservation lowers availability
    from apps.orders import services as orders
    orders.create_order(Actor.from_user(market.buyer), items=[{"listing_id": small.id, "quantity": Decimal("4"), "quantity_unit": "kg"}], delivery_method="collection")
    assert ids(min_quantity="2") == {"Tomatoes"}
    assert market.client().get(URL, {"min_quantity": "-1"}).status_code == 400


def test_ordering_options(market):
    _second(market, "10", produce_name="Cheap", price_per_unit="10.00")
    _second(market, "10", produce_name="Pricey", price_per_unit="500.00")
    names = lambda o: [i["produce_name"] for i in market.client().get(URL, {"ordering": o}).json()["data"]]  # noqa: E731
    assert names("price_asc")[0] == "Cheap" and names("price_desc")[0] == "Pricey"
    assert names("newest")[0] == "Pricey"
    assert market.client().get(URL, {"ordering": "random"}).status_code == 400
