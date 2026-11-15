import pytest

from apps.issues import services
from core.actor import Actor
from core.errors import ConflictError, ForbiddenError, InvalidInputError, NotFoundError

pytestmark = pytest.mark.django_db
DESC = "Half of the tomatoes were bruised on arrival."


def report(m, order, user=None, category="quality", description=DESC):
    return m.client(user or m.buyer).post(f"/api/v1/orders/{order.id}/issues", {"category": category, "description": description}, format="json")


def test_buyer_and_farmer_can_report_on_paid_order(market):
    order = market.pay(market.place())
    r = report(market, order)
    assert r.status_code == 201 and r.json()["data"]["status"] == "open"
    assert report(market, order, user=market.farmer, category="payment").status_code == 201


def test_completed_order_reportable_unpaid_not(market):
    assert report(market, market.complete(market.place())).status_code == 201
    r = report(market, market.place())
    assert r.status_code == 409 and r.json()["error"]["code"] == "ORDER_NOT_REPORTABLE"


def test_strangers_get_404_and_anonymous_401(market):
    order = market.pay(market.place())
    assert report(market, order, user=market.make_user("buyer")).status_code == 404
    assert report(market, order, user=market.make_user("farmer")).status_code == 404
    assert market.client().post(f"/api/v1/orders/{order.id}/issues", {}, format="json").status_code == 401


@pytest.mark.parametrize("override", [{"category": "weather"}, {"description": "short"}, {"description": ""}])
def test_validation(market, override):
    order = market.pay(market.place())
    assert report(market, order, **override).status_code == 400


def test_open_issue_cap(market):
    order = market.pay(market.place())
    for _ in range(services.MAX_OPEN_PER_ORDER):
        assert report(market, order).status_code == 201
    assert report(market, order).status_code == 409


def test_list_is_scoped_to_reporter_admin_sees_all(market):
    order = market.pay(market.place())
    report(market, order)
    report(market, order, user=market.farmer)
    mine = market.client(market.buyer).get(f"/api/v1/orders/{order.id}/issues").json()["data"]
    assert len(mine) == 1
    assert len(market.client(market.admin).get(f"/api/v1/orders/{order.id}/issues").json()["data"]) == 2
    assert market.client(market.make_user("buyer")).get(f"/api/v1/orders/{order.id}/issues").status_code == 404


def test_admin_triage_flow(market):
    from apps.notifications import selectors

    order = market.pay(market.place())
    iid = report(market, order).json()["data"]["id"]
    admin = Actor.from_user(market.admin)
    assert services.update_issue(admin, iid, "investigating").status == "investigating"
    with pytest.raises(InvalidInputError):
        services.update_issue(admin, iid, "resolved")  # needs a note
    done = services.update_issue(admin, iid, "resolved", "Partial refund agreed offline.")
    assert done.status == "resolved" and done.handled_by == market.admin.id
    with pytest.raises(ConflictError):
        services.update_issue(admin, iid, "open")
    services.update_issue(admin, iid, "resolved", "Partial refund agreed offline.")  # idempotent
    assert "issue_updated" in {n.kind for n in selectors.list_for_recipient(market.buyer.id)}


def test_only_admin_and_unknown_issue(market):
    order = market.pay(market.place())
    iid = report(market, order).json()["data"]["id"]
    with pytest.raises(ForbiddenError):
        services.update_issue(Actor.from_user(market.farmer), iid, "investigating")
    with pytest.raises(NotFoundError):
        services.update_issue(Actor.from_user(market.admin), "00000000-0000-0000-0000-000000000000", "investigating")
    with pytest.raises(InvalidInputError):
        services.update_issue(Actor.from_user(market.admin), iid, "bogus")
