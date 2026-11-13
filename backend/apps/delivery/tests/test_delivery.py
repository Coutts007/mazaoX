import pytest

from apps.notifications import selectors as notifications
from apps.orders import selectors as orders
from apps.payments import services as payments
from core.actor import Actor

pytestmark = pytest.mark.django_db


@pytest.fixture
def paid(shop):
    order = shop["place"]()
    buyer = Actor.from_user(shop["buyer"])
    attempt, _ = payments.start_simulated_payment(buyer, order.id)
    payments.complete_simulated_payment(buyer, attempt.id, "success")
    shop["admin"] = shop["make_user"]("admin")
    shop["order"] = order
    return shop


def create(shop, user="admin", order=None):
    return shop["client"](shop[user]).post(f"/api/v1/orders/{(order or shop['order']).id}/delivery")


def patch(shop, did, status, user="admin", **kw):
    return shop["client"](shop[user]).patch(f"/api/v1/deliveries/{did}", {"status": status, **kw}, format="json")


def test_admin_creates_delivery_for_paid_order(paid):
    r = create(paid)
    assert r.status_code == 201
    d = r.json()["data"]
    assert d["status"] == "pending" and d["method"] == "collection" and d["order_id"] == str(paid["order"].id)
    assert [e["to_status"] for e in d["events"]] == ["pending"]


@pytest.mark.parametrize("user", ["farmer", "buyer"])
def test_non_admins_cannot_create_or_update(paid, user):
    assert create(paid, user).status_code == 403
    did = create(paid).json()["data"]["id"]
    assert patch(paid, did, "dispatched", user).status_code == 403


def test_unauthenticated(paid):
    assert paid["client"]().post(f"/api/v1/orders/{paid['order'].id}/delivery").status_code == 401
    assert paid["client"]().patch("/api/v1/deliveries/00000000-0000-0000-0000-000000000000", {}, format="json").status_code == 401


def test_cannot_create_for_unpaid_or_unknown_order(shop):
    shop["admin"] = shop["make_user"]("admin")
    unpaid = shop["place"]()
    r = shop["client"](shop["admin"]).post(f"/api/v1/orders/{unpaid.id}/delivery")
    assert r.status_code == 409 and r.json()["error"]["code"] == "ORDER_NOT_PAID"
    assert shop["client"](shop["admin"]).post("/api/v1/orders/00000000-0000-0000-0000-000000000000/delivery").status_code == 404


def test_duplicate_delivery_is_409(paid):
    create(paid)
    r = create(paid)
    assert r.status_code == 409 and r.json()["error"]["code"] == "DELIVERY_EXISTS"


def test_full_lifecycle_completes_order_and_notifies_buyer(paid):
    did = create(paid).json()["data"]["id"]
    assert patch(paid, did, "dispatched", note="Left the farm").json()["data"]["status"] == "dispatched"
    done = patch(paid, did, "delivered")
    assert done.status_code == 200 and done.json()["data"]["status"] == "delivered"
    order = orders.get_order(paid["order"].id)
    assert order.status == "completed"
    assert [h.to_status for h in order.history.all()] == ["pending_payment", "paid", "completed"]
    kinds = {n.kind for n in notifications.list_for_recipient(paid["buyer"].id)}
    assert {"delivery_dispatched", "delivery_delivered"} <= kinds
    assert [e["to_status"] for e in done.json()["data"]["events"]] == ["pending", "dispatched", "delivered"]


@pytest.mark.parametrize(
    "path",
    [["delivered"], ["dispatched", "delivered", "failed"], ["dispatched", "delivered", "pending"]],
)
def test_invalid_transitions(paid, path):
    did = create(paid).json()["data"]["id"]
    *ok, last = path
    for s in ok:
        assert patch(paid, did, s).status_code == 200
    r = patch(paid, did, last)
    assert r.status_code == 409 and r.json()["error"]["code"] == "INVALID_TRANSITION"


def test_same_status_is_idempotent_and_failed_can_reschedule(paid):
    did = create(paid).json()["data"]["id"]
    assert patch(paid, did, "pending").status_code == 200
    assert patch(paid, did, "failed", note="Buyer unreachable").status_code == 200
    assert patch(paid, did, "failed").status_code == 200
    assert patch(paid, did, "pending").json()["data"]["status"] == "pending"
    assert orders.get_order(paid["order"].id).status == "paid"  # failure does not complete the order


def test_unknown_status_and_delivery(paid):
    did = create(paid).json()["data"]["id"]
    assert patch(paid, did, "teleported").status_code == 400
    assert patch(paid, "00000000-0000-0000-0000-000000000000", "dispatched").status_code == 404


def test_view_delivery_participants_only(paid):
    url = f"/api/v1/orders/{paid['order'].id}/delivery"
    assert paid["client"](paid["buyer"]).get(url).status_code == 404  # none created yet
    create(paid)
    c = paid["client"]
    for user in ("buyer", "farmer", "admin"):
        assert c(paid[user]).get(url).status_code == 200
    assert c(paid["make_user"]("buyer")).get(url).status_code == 404
    assert c(paid["make_user"]("farmer")).get(url).status_code == 404
    assert c().get(url).status_code == 401


def test_completed_order_cannot_be_cancelled(paid):
    from core.errors import ConflictError
    from apps.orders import services as order_services

    did = create(paid).json()["data"]["id"]
    patch(paid, did, "dispatched")
    patch(paid, did, "delivered")
    with pytest.raises(ConflictError):
        order_services.cancel_order(Actor.from_user(paid["buyer"]), paid["order"].id)
