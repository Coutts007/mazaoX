import json

import pytest
from django.core.management import call_command
from django.core.management.base import SystemCheckError  # noqa: F401

pytestmark = pytest.mark.django_db


def start(shop, order, user="buyer"):
    return shop["client"](shop[user]).post(f"/api/v1/orders/{order.id}/payment-simulation", {}, format="json")


def complete(shop, pid, outcome="success", user="buyer"):
    return shop["client"](shop[user]).post(f"/api/v1/payments/simulations/{pid}/complete", {"outcome": outcome}, format="json")


def test_full_happy_path_over_http(shop):
    order = shop["place"]("10")
    r = start(shop, order)
    assert r.status_code == 201
    d = r.json()["data"]
    assert d["status"] == "pending" and d["amount"] == "850.00" and d["currency"] == "KSh" and d["mode"] == "simulated"
    done = complete(shop, d["id"])
    assert done.status_code == 200 and done.json()["data"]["status"] == "succeeded"
    got = shop["client"](shop["buyer"]).get(f"/api/v1/orders/{order.id}").json()["data"]
    assert got["status"] == "paid" and got["payment_due_by"] is None
    assert shop["client"](shop["buyer"]).get(f"/api/v1/payments/simulations/{d['id']}").json()["data"]["status"] == "succeeded"


def test_start_ignores_body_and_stores_no_credentials(shop):
    order = shop["place"]()
    r = shop["client"](shop["buyer"]).post(
        f"/api/v1/orders/{order.id}/payment-simulation",
        {"amount": "1.00", "phone": "0712345678", "pin": "1234", "card_cvv": "123"}, format="json")
    assert r.status_code == 201
    text = json.dumps(r.json())
    assert r.json()["data"]["amount"] == "850.00"
    assert "1234" not in text and "0712345678" not in text and "pin" not in r.json()["data"]


def test_start_authorization(shop):
    order = shop["place"]()
    assert start(shop, order, "farmer").status_code == 403
    assert shop["client"]().post(f"/api/v1/orders/{order.id}/payment-simulation").status_code == 401
    stranger = shop["make_user"]("buyer")
    assert shop["client"](stranger).post(f"/api/v1/orders/{order.id}/payment-simulation").status_code == 404


def test_start_twice_returns_same_attempt(shop):
    order = shop["place"]()
    a, b = start(shop, order), start(shop, order)
    assert (a.status_code, b.status_code) == (201, 200) and a.json()["data"]["id"] == b.json()["data"]["id"]


def test_complete_validation_and_authorization(shop):
    order = shop["place"]()
    pid = start(shop, order).json()["data"]["id"]
    assert complete(shop, pid, "maybe").status_code == 400
    assert complete(shop, pid, user="farmer").status_code == 404
    assert shop["client"]().post(f"/api/v1/payments/simulations/{pid}/complete", {"outcome": "success"}, format="json").status_code == 401
    assert shop["client"](shop["buyer"]).post(f"/api/v1/payments/simulations/{pid}/complete", {}, format="json").status_code == 400


def test_conflicting_completion_is_409(shop):
    order = shop["place"]()
    pid = start(shop, order).json()["data"]["id"]
    assert complete(shop, pid, "success").status_code == 200
    r = complete(shop, pid, "failure")
    assert r.status_code == 409 and r.json()["error"]["code"] == "PAYMENT_ALREADY_COMPLETED"


def test_completion_endpoint_looks_missing_when_disabled(shop, settings):
    order = shop["place"]()
    pid = start(shop, order).json()["data"]["id"]
    settings.PAYMENT_SIMULATION_ENABLED = False
    r = complete(shop, pid)
    assert r.status_code == 404
    assert shop["client"](shop["buyer"]).get(f"/api/v1/orders/{order.id}").json()["data"]["status"] == "pending_payment"


def test_payment_detail_visibility(shop):
    order = shop["place"]()
    pid = start(shop, order).json()["data"]["id"]
    assert shop["client"](shop["farmer"]).get(f"/api/v1/payments/simulations/{pid}").status_code == 404
    assert shop["client"](shop["make_user"]("admin")).get(f"/api/v1/payments/simulations/{pid}").status_code == 200


def test_system_check_warns_when_simulation_on_in_production(settings):
    from django.core.checks import run_checks

    settings.DEBUG, settings.PAYMENT_SIMULATION_ENABLED = False, True
    assert "mazaox.W001" in [m.id for m in run_checks()]
    settings.PAYMENT_SIMULATION_ENABLED = False
    assert "mazaox.W001" not in [m.id for m in run_checks()]
