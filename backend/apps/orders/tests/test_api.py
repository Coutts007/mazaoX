import uuid

import pytest

pytestmark = pytest.mark.django_db
ORDERS = "/api/v1/orders"


def body(shop, **kw):
    data = {"items": [{"listing_id": str(shop["tomatoes"].id), "quantity": "10.000", "quantity_unit": "kg"}],
            "delivery_method": "collection", "delivery_location": "Agreed collection point"}
    data.update(kw)
    return data


def post(shop, user="buyer", key=None, **kw):
    headers = {"HTTP_IDEMPOTENCY_KEY": key} if key else {}
    return shop["client"](shop[user] if isinstance(user, str) else user).post(ORDERS, body(shop, **kw), format="json", **headers)


def test_create_order_response(shop):
    r = post(shop)
    assert r.status_code == 201
    d = r.json()["data"]
    assert d["status"] == "pending_payment" and d["total_amount"] == "850.00" and d["currency"] == "KSh"
    assert d["payment_due_by"] and d["lines"][0]["unit_price"] == "85.00"


def test_client_supplied_prices_and_totals_are_ignored(shop):
    payload = body(shop, total_amount="1.00")
    payload["items"][0]["unit_price"] = "0.01"
    r = shop["client"](shop["buyer"]).post(ORDERS, payload, format="json")
    assert r.status_code == 201
    assert r.json()["data"]["total_amount"] == "850.00"


def test_authorization(shop):
    assert post(shop, user="farmer").status_code == 403
    assert shop["client"]().post(ORDERS, body(shop), format="json").status_code == 401
    assert shop["client"]().get(ORDERS).status_code == 401


@pytest.mark.parametrize(
    "override",
    [{"items": []}, {"items": [{"listing_id": "x", "quantity": "1", "quantity_unit": "kg"}]},
     {"delivery_method": "teleport"}, {"items": [{"quantity": "1", "quantity_unit": "kg"}]}],
)
def test_validation_errors(shop, override):
    r = post(shop, **override)
    assert r.status_code == 400 and r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_insufficient_stock_is_409_with_line_field(shop):
    r = post(shop, items=[{"listing_id": str(shop["tomatoes"].id), "quantity": "101", "quantity_unit": "kg"}])
    assert r.status_code == 409
    err = r.json()["error"]
    assert err["code"] == "INSUFFICIENT_STOCK" and err["details"][0]["field"] == "items.0.quantity"


def test_unknown_listing_is_400(shop):
    r = post(shop, items=[{"listing_id": str(uuid.uuid4()), "quantity": "1", "quantity_unit": "kg"}])
    assert r.status_code == 400


def test_idempotency_key_replay_and_conflict(shop):
    first = post(shop, key="abcd-1234-efgh")
    replay = post(shop, key="abcd-1234-efgh")
    assert first.status_code == 201 and replay.status_code == 200
    assert replay["Idempotent-Replay"] == "true"
    assert first.json()["data"]["id"] == replay.json()["data"]["id"]
    changed = post(shop, key="abcd-1234-efgh", items=[{"listing_id": str(shop["tomatoes"].id), "quantity": "11", "quantity_unit": "kg"}])
    assert changed.status_code == 409 and changed.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"


def test_bad_idempotency_key_rejected(shop):
    assert post(shop, key="short").status_code == 400
    assert post(shop, key="has spaces in it!").status_code == 400


def test_detail_visibility(shop):
    oid = post(shop).json()["data"]["id"]
    c = shop["client"]
    stranger, other_farmer = shop["make_user"]("buyer"), shop["make_user"]("farmer")
    admin = shop["make_user"]("admin")
    assert c(shop["buyer"]).get(f"{ORDERS}/{oid}").status_code == 200
    assert c(shop["farmer"]).get(f"{ORDERS}/{oid}").status_code == 200
    assert c(admin).get(f"{ORDERS}/{oid}").status_code == 200
    assert c(stranger).get(f"{ORDERS}/{oid}").status_code == 404
    assert c(other_farmer).get(f"{ORDERS}/{oid}").status_code == 404
    assert c(stranger).get(f"{ORDERS}/{oid}/history").status_code == 404
    assert c().get(f"{ORDERS}/{oid}").status_code == 401
    assert c(shop["buyer"]).get(f"{ORDERS}/not-a-uuid").status_code == 404


def test_list_is_scoped_paginated_and_filterable(shop):
    for _ in range(3):
        post(shop)
    post(shop, user=shop["make_user"]("buyer"))
    c = shop["client"]
    r = c(shop["buyer"]).get(ORDERS, {"page_size": 2}).json()
    assert len(r["data"]) == 2 and r["pagination"]["total_items"] == 3
    assert c(shop["farmer"]).get(ORDERS).json()["pagination"]["total_items"] == 4
    assert c(shop["buyer"]).get(ORDERS, {"status": "cancelled"}).json()["data"] == []
    assert c(shop["buyer"]).get(ORDERS, {"status": "bogus"}).status_code == 400


def test_cancel_and_history(shop):
    oid = post(shop).json()["data"]["id"]
    c = shop["client"]
    assert c(shop["make_user"]("buyer")).post(f"{ORDERS}/{oid}/cancel").status_code == 404
    r = c(shop["buyer"]).post(f"{ORDERS}/{oid}/cancel", {"reason": "Changed my mind"}, format="json")
    assert r.status_code == 200 and r.json()["data"]["status"] == "cancelled" and r.json()["data"]["payment_due_by"] is None
    hist = c(shop["buyer"]).get(f"{ORDERS}/{oid}/history").json()["data"]
    assert [h["to_status"] for h in hist] == ["pending_payment", "cancelled"]
    assert hist[1]["note"] == "Changed my mind"
    assert c(shop["buyer"]).get(f"/api/v1/inventory/listings/{shop['tomatoes'].id}/availability").json()["data"]["available"] == "100.000"
