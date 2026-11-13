import pytest

pytestmark = pytest.mark.django_db


@pytest.fixture
def env(make_user, make_listing, auth_client):
    farmer, other, buyer = make_user("farmer"), make_user("farmer"), make_user("buyer")
    admin = make_user("admin")
    listing = make_listing(farmer)
    return dict(farmer=farmer, other=other, buyer=buyer, admin=admin, listing=listing, client=auth_client)


def url(env, tail=""):
    return f"/api/v1/inventory/listings/{env['listing'].id}{tail}"


def add(env, qty="50.000", user="farmer", **kw):
    body = {"movement_type": "addition", "quantity": qty, "reason": "New harvest recorded"}
    body.update(kw)
    return env["client"](env[user]).post(url(env, "/adjustments"), body, format="json")


def test_adjustment_response_and_summary(env):
    r = add(env)
    assert r.status_code == 201
    data = r.json()["data"]
    assert data["movement"]["resulting_on_hand"] == "50.000"
    assert data["summary"]["available"] == "50.000"
    s = env["client"](env["farmer"]).get(url(env)).json()["data"]
    assert (s["on_hand"], s["reserved"], s["available"], s["unit"]) == ("50.000", "0.000", "50.000", "kg")


def test_adjustment_authorization(env):
    assert add(env, user="other").status_code == 403
    assert add(env, user="buyer").status_code == 403
    assert add(env, user="admin").status_code == 403
    assert env["client"]().post(url(env, "/adjustments"), {}, format="json").status_code == 401


@pytest.mark.parametrize(
    "override,field",
    [
        ({"quantity": "0"}, "quantity"),
        ({"quantity": "-3"}, "quantity"),
        ({"quantity": "abc"}, "quantity"),
        ({"movement_type": "sale"}, "movement_type"),
        ({"movement_type": "correction", "reason": ""}, "reason"),
    ],
)
def test_adjustment_validation(env, override, field):
    r = add(env, **override)
    assert r.status_code == 400
    assert field in [d["field"] for d in r.json()["error"]["details"]]


def test_negative_stock_is_a_409(env):
    add(env, "5")
    r = add(env, "6", movement_type="spoilage", reason="loss")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "INSUFFICIENT_STOCK"


def test_summary_and_movements_visibility(env):
    add(env)
    c = env["client"]
    assert c(env["admin"]).get(url(env)).status_code == 200
    assert c(env["other"]).get(url(env)).status_code == 403
    assert c(env["buyer"]).get(url(env, "/movements")).status_code == 403
    assert c().get(url(env)).status_code == 401
    r = c(env["farmer"]).get(url(env, "/movements"))
    assert r.status_code == 200
    assert r.json()["pagination"]["total_items"] == 1
    assert r.json()["data"][0]["reason"] == "New harvest recorded"


def test_unknown_listing_is_404(env):
    bad = "/api/v1/inventory/listings/00000000-0000-0000-0000-000000000000"
    assert env["client"](env["farmer"]).get(bad).status_code == 404


def test_public_availability_hides_on_hand(env):
    add(env, "20")
    r = env["client"]().get(url(env, "/availability"))
    assert r.status_code == 200
    assert r.json()["data"] == {"listing_id": str(env["listing"].id), "unit": "kg", "available": "20.000", "in_stock": True}


def test_public_availability_no_stock_and_inactive(env):
    assert env["client"]().get(url(env, "/availability")).json()["data"]["in_stock"] is False
    env["client"](env["farmer"]).post(f"/api/v1/listings/{env['listing'].id}/deactivate")
    assert env["client"]().get(url(env, "/availability")).status_code == 404
