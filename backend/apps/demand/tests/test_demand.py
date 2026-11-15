from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.demand import services
from apps.inventory import selectors as inv
from apps.inventory import services as inventory
from apps.notifications import selectors as notifications
from core.actor import Actor

pytestmark = pytest.mark.django_db
URL = "/api/v1/demand-requests"


def body(**kw):
    data = {"produce_name": "Tomatoes", "quantity": "200.000", "quantity_unit": "kg", "target_price_per_unit": "90.00",
            "county": "Kiambu", "required_by": str(date.today() + timedelta(days=7))}
    data.update(kw)
    return data


def create(m, user=None, **kw):
    return m.client(user or m.buyer).post(URL, body(**kw), format="json")


def test_buyer_creates_and_reads_request(market):
    r = create(market)
    assert r.status_code == 201
    d = r.json()["data"]
    assert d["status"] == "open" and d["county"] == "Kiambu" and d["quantity"] == "200.000"
    assert market.client(market.buyer).get(f"{URL}/{d['id']}").status_code == 200


def test_authorization(market):
    assert create(market, market.farmer).status_code == 403
    assert market.client().post(URL, body(), format="json").status_code == 401
    rid = create(market).json()["data"]["id"]
    stranger = market.make_user("buyer")
    assert market.client(stranger).get(f"{URL}/{rid}").status_code == 404
    assert market.client(stranger).post(f"{URL}/{rid}/close").status_code == 404
    assert market.client(stranger).get(f"{URL}/{rid}/matches").status_code == 404
    assert market.client(market.admin).get(f"{URL}/{rid}").status_code == 200


@pytest.mark.parametrize(
    "override,field",
    [({"quantity": "0"}, "quantity"), ({"quantity_unit": "litre"}, "quantity_unit"), ({"county": "Atlantis"}, "county"),
     ({"target_price_per_unit": "0"}, "target_price_per_unit"), ({"produce_name": "  "}, "produce_name"),
     ({"required_by": str(date.today() - timedelta(days=1))}, "required_by"), ({"required_by": "soon"}, "required_by")],
)
def test_validation(market, override, field):
    r = create(market, **override)
    assert r.status_code == 400 and field in [d["field"] for d in r.json()["error"]["details"]]


def test_price_is_optional(market):
    payload = body()
    del payload["target_price_per_unit"]
    assert market.client(market.buyer).post(URL, payload, format="json").status_code == 201


def test_list_scoped_paginated_and_filtered(market):
    for _ in range(3):
        create(market)
    other = market.make_user("buyer")
    create(market, other)
    assert market.client(market.buyer).get(URL, {"page_size": 2}).json()["pagination"]["total_items"] == 3
    assert market.client(market.admin).get(URL).json()["pagination"]["total_items"] == 4
    assert market.client(market.buyer).get(URL, {"status": "closed"}).json()["data"] == []
    assert market.client(market.buyer).get(URL, {"status": "bogus"}).status_code == 400
    assert market.client(market.farmer).get(URL).json()["data"] == []  # farmers do not own requests


def test_close_is_idempotent_and_blocks_matches(market):
    rid = create(market).json()["data"]["id"]
    c = market.client(market.buyer)
    assert c.post(f"{URL}/{rid}/close").json()["data"]["status"] == "closed"
    assert c.post(f"{URL}/{rid}/close").status_code == 200
    r = c.get(f"{URL}/{rid}/matches")
    assert r.status_code == 409 and r.json()["error"]["code"] == "REQUEST_NOT_OPEN"


def test_open_request_cap(market, monkeypatch):
    monkeypatch.setattr(services, "MAX_OPEN_PER_BUYER", 2)
    create(market), create(market)
    r = create(market)
    assert r.status_code == 409 and r.json()["error"]["code"] == "TOO_MANY_OPEN_REQUESTS"


def _other_listing(market, **kw):
    farmer = market.make_user("farmer")
    stock = kw.pop("stock", "50")
    listing = market.make_listing(farmer, **kw)
    if Decimal(stock) > 0:
        inventory.adjust_stock(Actor.from_user(farmer), listing.id, "addition", Decimal(stock))
    return farmer, listing


def test_matching_scores_ranks_and_excludes(market):
    cheap_far, far = _other_listing(market, county="Nakuru", price_per_unit="120.00", stock="50")  # name+unit only, partial stock
    _, empty = _other_listing(market, stock="0")  # no stock -> excluded
    _, sacks = _other_listing(market, quantity_unit="bag", stock="500")  # different unit -> excluded
    _, onions = _other_listing(market, produce_name="Onions", stock="500")  # different produce -> excluded
    rid = create(market).json()["data"]["id"]
    r = market.client(market.buyer).get(f"{URL}/{rid}/matches")
    assert r.status_code == 200 and r.json()["informational"] is True
    data = r.json()["data"]
    ids = [m["listing"]["id"] for m in data]
    assert ids == [str(market.listing.id), str(far.id)]
    best, second = data
    assert best["score"] == 100 and set(best["reasons"]) == {"name", "unit", "county", "within_target_price", "enough_stock"}
    assert second["score"] == 60 and second["reasons"] == ["name", "unit"] and second["available"] == "50.000"
    assert str(empty.id) not in ids and str(sacks.id) not in ids and str(onions.id) not in ids


def test_matching_never_reserves_stock_or_creates_orders(market):
    before = inv.get_availability(market.listing.id).available
    rid = create(market).json()["data"]["id"]
    market.client(market.buyer).get(f"{URL}/{rid}/matches")
    assert inv.get_availability(market.listing.id).available == before
    assert market.client(market.buyer).get("/api/v1/orders").json()["data"] == []


def test_matching_skips_hidden_listings(market):
    market.client(market.admin).patch(f"/api/v1/admin/listings/{market.listing.id}/moderation", {"hidden": True, "reason": "x"}, format="json")
    rid = create(market).json()["data"]["id"]
    assert market.client(market.buyer).get(f"{URL}/{rid}/matches").json()["data"] == []


def test_matching_farmers_are_notified_without_buyer_identity(market):
    unrelated, _ = _other_listing(market, produce_name="Onions")
    create(market)
    notes = list(notifications.list_for_recipient(market.farmer.id))
    assert [n.kind for n in notes] == ["demand_match"]
    assert "200 kg of Tomatoes in Kiambu" in notes[0].message
    assert market.buyer.full_name not in notes[0].message and str(market.buyer.id) not in notes[0].message
    assert list(notifications.list_for_recipient(unrelated.id)) == []


def test_market_view_for_farmers_hides_buyer(market):
    create(market)
    create(market, produce_name="Maize", county="Nakuru")
    r = market.client(market.farmer).get(f"{URL}/market")
    assert r.status_code == 200 and r.json()["pagination"]["total_items"] == 2
    assert "buyer" not in r.content.decode().lower() or str(market.buyer.id) not in r.content.decode()
    assert market.client(market.farmer).get(f"{URL}/market", {"produce": "maize"}).json()["pagination"]["total_items"] == 1
    assert market.client(market.farmer).get(f"{URL}/market", {"county": "kiambu"}).json()["pagination"]["total_items"] == 1
    assert market.client(market.buyer).get(f"{URL}/market").status_code == 403
    assert market.client().get(f"{URL}/market").status_code == 401


def test_expiry_sweep(market):
    rid = create(market).json()["data"]["id"]
    assert services.expire_overdue(today=date.today() + timedelta(days=30)) == 1
    assert services.expire_overdue(today=date.today() + timedelta(days=30)) == 0
    assert market.client(market.buyer).get(f"{URL}/{rid}").json()["data"]["status"] == "expired"
    assert market.client(market.farmer).get(f"{URL}/market").json()["data"] == []
