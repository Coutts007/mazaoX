import uuid

import pytest

from apps.notifications import selectors, services
from apps.orders import services as order_services
from apps.payments import services as payments
from core.actor import Actor

pytestmark = pytest.mark.django_db
URL = "/api/v1/notifications"


def kinds(user):
    return sorted(n.kind for n in selectors.list_for_recipient(user.id))


def test_order_placed_notifies_buyer_and_farmer(shop):
    shop["place"]()
    assert kinds(shop["buyer"]) == ["order_placed"]
    assert kinds(shop["farmer"]) == ["order_received"]


def test_payment_success_notifies_both(shop):
    order = shop["place"]()
    buyer = Actor.from_user(shop["buyer"])
    attempt, _ = payments.start_simulated_payment(buyer, order.id)
    payments.complete_simulated_payment(buyer, attempt.id, "success")
    assert "payment_received" in kinds(shop["buyer"]) and "order_paid" in kinds(shop["farmer"])


def test_payment_failure_notifies_buyer_only(shop):
    order = shop["place"]()
    buyer = Actor.from_user(shop["buyer"])
    attempt, _ = payments.start_simulated_payment(buyer, order.id)
    payments.complete_simulated_payment(buyer, attempt.id, "failure")
    assert "payment_failed" in kinds(shop["buyer"]) and "payment_failed" not in kinds(shop["farmer"])


def test_cancel_notifies_the_other_party_only(shop):
    order = shop["place"]()
    order_services.cancel_order(Actor.from_user(shop["buyer"]), order.id)
    assert "order_cancelled" in kinds(shop["farmer"]) and "order_cancelled" not in kinds(shop["buyer"])


def test_admin_cancel_notifies_both(shop):
    order = shop["place"]()
    order_services.cancel_order(Actor(uuid.uuid4(), "admin"), order.id)
    assert "order_cancelled" in kinds(shop["farmer"]) and "order_cancelled" in kinds(shop["buyer"])


def test_expiry_notifies_buyer(shop, monkeypatch):
    from datetime import timedelta

    from django.utils import timezone

    shop["place"]()
    later = timezone.now() + timedelta(minutes=30)
    monkeypatch.setattr("apps.orders.services.timezone.now", lambda: later)
    assert order_services.expire_unpaid_orders() == 1
    assert "order_expired" in kinds(shop["buyer"])


def test_notify_failure_never_breaks_the_caller(shop, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("db hiccup")

    monkeypatch.setattr("apps.notifications.services.Notification.objects.create", boom)
    order = shop["place"]()  # must still succeed
    assert order.status == "pending_payment"
    assert kinds(shop["buyer"]) == []


def test_notification_rolls_back_with_failed_order(shop):
    from core.errors import ConflictError

    with pytest.raises(ConflictError):
        shop["place"]("101")  # more than the 100 kg in stock
    assert kinds(shop["buyer"]) == [] and kinds(shop["farmer"]) == []


def test_api_lists_only_own_notifications_with_unread_count(shop):
    shop["place"]()
    c = shop["client"]
    r = c(shop["buyer"]).get(URL)
    assert r.status_code == 200
    body = r.json()
    assert body["pagination"]["total_items"] == 1 and body["unread_count"] == 1
    assert body["data"][0]["kind"] == "order_placed" and body["data"][0]["is_read"] is False
    assert c(shop["make_user"]("buyer")).get(URL).json()["data"] == []
    assert c().get(URL).status_code == 401


def test_mark_read_and_unread_filter(shop):
    shop["place"]()
    c = shop["client"](shop["buyer"])
    nid = c.get(URL).json()["data"][0]["id"]
    r = c.post(f"{URL}/{nid}/read")
    assert r.status_code == 200 and r.json()["data"]["is_read"] is True
    assert c.post(f"{URL}/{nid}/read").status_code == 200  # idempotent
    body = c.get(URL, {"unread": "true"}).json()
    assert body["data"] == [] and body["unread_count"] == 0
    assert len(c.get(URL).json()["data"]) == 1
    assert c.get(URL, {"unread": "maybe"}).status_code == 400


def test_cannot_read_someone_elses_notification(shop):
    shop["place"]()
    nid = shop["client"](shop["buyer"]).get(URL).json()["data"][0]["id"]
    assert shop["client"](shop["farmer"]).post(f"{URL}/{nid}/read").status_code == 404
    assert shop["client"]().post(f"{URL}/{nid}/read").status_code == 401
    assert shop["client"](shop["buyer"]).post(f"{URL}/not-a-uuid/read").status_code == 404
    assert selectors.unread_count(shop["buyer"].id) == 1


def test_pagination(shop):
    for _ in range(3):
        services.notify(shop["buyer"].id, "x", "T", "M")
    r = shop["client"](shop["buyer"]).get(URL, {"page_size": 2}).json()
    assert len(r["data"]) == 2 and r["pagination"]["total_items"] == 3
