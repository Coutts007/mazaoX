import pytest

from apps.audit import selectors as audit

pytestmark = pytest.mark.django_db
A = "/api/v1/admin"


def test_every_admin_route_requires_admin(market):
    routes = [("get", "/users"), ("get", "/listings"), ("get", "/issues"), ("get", "/reviews"),
              ("get", "/reports/summary"), ("get", "/audit-logs")]
    for user in (market.farmer, market.buyer):
        for method, path in routes:
            assert getattr(market.client(user), method)(A + path).status_code == 403, path
    for method, path in routes:
        assert getattr(market.client(), method)(A + path).status_code == 401, path


def test_user_search_filters_and_pagination(market):
    c = market.client(market.admin)
    body = c.get(f"{A}/users", {"role": "farmer"}).json()
    assert body["pagination"]["total_items"] == 1 and body["data"][0]["role"] == "farmer"
    assert c.get(f"{A}/users", {"q": market.buyer.email[:8]}).json()["pagination"]["total_items"] >= 1
    assert c.get(f"{A}/users", {"role": "wizard"}).status_code == 400
    assert c.get(f"{A}/users", {"is_active": "maybe"}).status_code == 400
    assert "password" not in c.get(f"{A}/users").content.decode()
    assert c.get(f"{A}/users", {"page_size": 1}).json()["pagination"]["total_pages"] == 3


def test_suspend_farmer_hides_listings_blocks_login_and_is_audited(market):
    c = market.client(market.admin)
    lid = str(market.listing.id)
    assert market.client().get(f"/api/v1/listings/{lid}").status_code == 200
    r = c.patch(f"{A}/users/{market.farmer.id}/status", {"is_active": False, "reason": "Fraud reports"}, format="json")
    assert r.status_code == 200 and r.json()["data"]["is_active"] is False
    assert market.client().get(f"/api/v1/listings/{lid}").status_code == 404
    assert market.client().get("/api/v1/listings").json()["data"] == []
    login = market.client().post("/api/v1/auth/login", {"identifier": market.farmer.email, "password": "Str0ng-Example-Pass"}, format="json")
    assert login.status_code == 403
    # new orders for a suspended farmer's listing are refused
    from apps.orders import services as orders
    from core.actor import Actor
    from core.errors import InvalidInputError
    from decimal import Decimal
    with pytest.raises(InvalidInputError):
        orders.create_order(Actor.from_user(market.buyer), items=[{"listing_id": market.listing.id, "quantity": Decimal(1), "quantity_unit": "kg"}], delivery_method="collection")
    # reinstating restores everything
    c.patch(f"{A}/users/{market.farmer.id}/status", {"is_active": True}, format="json")
    assert market.client().get(f"/api/v1/listings/{lid}").status_code == 200
    log = audit.search(action="user.suspended").get()
    assert log.actor_id == market.admin.id and log.detail["reason"] == "Fraud reports" and log.detail["listings_affected"] == 1
    assert audit.search(action="user.reinstated").count() == 1


def test_suspend_rules(market):
    c = market.client(market.admin)
    url = lambda u: f"{A}/users/{u.id}/status"  # noqa: E731
    assert c.patch(url(market.buyer), {"is_active": False}, format="json").status_code == 400  # reason required
    assert c.patch(url(market.admin), {"is_active": False, "reason": "x"}, format="json").status_code == 400  # self
    other_admin = market.make_user("admin")
    assert c.patch(url(other_admin), {"is_active": False, "reason": "x"}, format="json").status_code == 400
    assert c.patch(f"{A}/users/00000000-0000-0000-0000-000000000000/status", {"is_active": False, "reason": "x"}, format="json").status_code == 404
    assert market.client(market.farmer).patch(url(market.buyer), {"is_active": False, "reason": "x"}, format="json").status_code == 403
    assert c.patch(url(market.buyer), {}, format="json").status_code == 400


def test_listing_moderation_flow(market):
    c = market.client(market.admin)
    lid = str(market.listing.id)
    assert c.get(f"{A}/listings").json()["pagination"]["total_items"] == 1
    assert c.patch(f"{A}/listings/{lid}/moderation", {"hidden": True}, format="json").status_code == 400
    r = c.patch(f"{A}/listings/{lid}/moderation", {"hidden": True, "reason": "Misleading photos"}, format="json")
    assert r.status_code == 200 and r.json()["data"]["moderation_hidden"] is True
    assert market.client().get(f"/api/v1/listings/{lid}").status_code == 404
    assert market.client(market.buyer).get(f"/api/v1/listings/{lid}").status_code == 404
    assert market.client(market.farmer).get(f"/api/v1/listings/{lid}").json()["data"]["moderation_reason"] == "Misleading photos"
    assert c.get(f"{A}/listings", {"hidden": "true"}).json()["pagination"]["total_items"] == 1
    assert market.client().get(f"/api/v1/inventory/listings/{lid}/availability").status_code == 404
    c.patch(f"{A}/listings/{lid}/moderation", {"hidden": False}, format="json")
    assert market.client().get(f"/api/v1/listings/{lid}").status_code == 200
    assert {a.action for a in audit.search(target_type="listing")} == {"listing.hidden", "listing.restored"}
    assert market.client(market.farmer).patch(f"{A}/listings/{lid}/moderation", {"hidden": True, "reason": "x"}, format="json").status_code == 403


def test_issue_handling_via_admin(market):
    order = market.pay(market.place())
    iid = market.client(market.buyer).post(f"/api/v1/orders/{order.id}/issues", {"category": "quality", "description": "Bruised produce on arrival."}, format="json").json()["data"]["id"]
    c = market.client(market.admin)
    assert c.get(f"{A}/issues", {"status": "open"}).json()["pagination"]["total_items"] == 1
    assert c.get(f"{A}/issues", {"status": "bogus"}).status_code == 400
    assert c.patch(f"{A}/issues/{iid}", {"status": "resolved"}, format="json").status_code == 400
    r = c.patch(f"{A}/issues/{iid}", {"status": "resolved", "resolution": "Refunded offline."}, format="json")
    assert r.status_code == 200 and r.json()["data"]["status"] == "resolved"
    assert audit.search(action="issue.updated").count() == 1


def test_review_moderation_via_admin(market):
    order = market.complete(market.place())
    rid = market.client(market.buyer).post(f"/api/v1/orders/{order.id}/reviews", {"rating": 1, "comment": "abusive text"}, format="json").json()["data"]["id"]
    c = market.client(market.admin)
    assert c.get(f"{A}/reviews").json()["pagination"]["total_items"] == 1
    c.patch(f"{A}/reviews/{rid}/moderation", {"hidden": True, "reason": "Abusive"}, format="json")
    pub = market.client().get(f"/api/v1/farmers/{market.farmer.id}/reviews").json()
    assert pub["data"] == [] and pub["summary"]["review_count"] == 0
    assert c.get(f"{A}/reviews").json()["data"][0]["is_hidden"] is True


def test_summary_report(market):
    market.complete(market.place())
    market.place()
    body = market.client(market.admin).get(f"{A}/reports/summary").json()["data"]
    assert body["users"]["by_role"] == {"farmer": 1, "buyer": 1, "admin": 1}
    assert body["orders"]["by_status"] == {"completed": 1, "pending_payment": 1}
    assert body["orders"]["paid_value_ksh"] == "850.00"
    assert body["listings"]["total"] == 1 and body["payments"]["by_status"] == {"succeeded": 1}
    assert body["deliveries"]["by_status"] == {"delivered": 1}
    assert set(body) == {"users", "listings", "orders", "payments", "deliveries", "issues", "reviews", "inspections"}


def test_audit_log_listing_and_secrets_stripped(market):
    from apps.audit import services

    services.record(market.admin.id, "x.test", "thing", "1", {"password": "hunter2", "token": "abc", "ok": "yes"})
    log = market.client(market.admin).get(f"{A}/audit-logs", {"action": "x.test"}).json()["data"][0]
    assert log["detail"] == {"ok": "yes"}
