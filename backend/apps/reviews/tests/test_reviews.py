import pytest

pytestmark = pytest.mark.django_db


def review(m, order, rating=5, comment="Fresh and on time", user=None):
    return m.client(user or m.buyer).post(f"/api/v1/orders/{order.id}/reviews", {"rating": rating, "comment": comment}, format="json")


def test_buyer_reviews_completed_order(market):
    order = market.complete(market.place())
    r = review(market, order)
    assert r.status_code == 201
    assert r.json()["data"]["rating"] == 5 and r.json()["data"]["order_id"] == str(order.id)


def test_review_requires_completed_order(market):
    pending = market.place()
    r = review(market, pending)
    assert r.status_code == 409 and r.json()["error"]["code"] == "ORDER_NOT_COMPLETED"
    paid = market.pay(market.place())
    assert review(market, paid).status_code == 409


def test_duplicate_review_is_409(market):
    order = market.complete(market.place())
    review(market, order)
    r = review(market, order, 3)
    assert r.status_code == 409 and r.json()["error"]["code"] == "REVIEW_EXISTS"


def test_review_authorization(market):
    order = market.complete(market.place())
    assert review(market, order, user=market.farmer).status_code == 403
    assert review(market, order, user=market.make_user("buyer")).status_code == 404
    assert market.client().post(f"/api/v1/orders/{order.id}/reviews", {"rating": 5}, format="json").status_code == 401


@pytest.mark.parametrize("rating", [0, 6, -1, "x", None])
def test_rating_bounds(market, rating):
    order = market.complete(market.place())
    r = review(market, order, rating)
    assert r.status_code == 400 and r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_public_list_summary_and_privacy(market):
    for rating in (5, 4, 3):
        review(market, market.complete(market.place()), rating, f"comment {rating}")
    r = market.client().get(f"/api/v1/farmers/{market.farmer.id}/reviews")
    assert r.status_code == 200
    body = r.json()
    assert body["summary"]["average_rating"] == 4.0 and body["summary"]["review_count"] == 3
    assert body["summary"]["distribution"] == {"1": 0, "2": 0, "3": 1, "4": 1, "5": 1}
    first = body["data"][0]
    assert first["reviewer"] == "Demo"  # first name only
    text = r.content.decode()
    assert market.buyer.email not in text and str(market.buyer.id) not in text
    assert body["pagination"]["total_items"] == 3


def test_public_list_empty_and_unknown_farmer(market):
    r = market.client().get(f"/api/v1/farmers/{market.farmer.id}/reviews").json()
    assert r["data"] == [] and r["summary"]["average_rating"] is None
    assert market.client().get("/api/v1/farmers/00000000-0000-0000-0000-000000000000/reviews").status_code == 404


def test_hidden_review_leaves_public_list_and_average(market):
    from apps.reviews import services
    from apps.reviews.models import Review  # noqa: F401 - guard allows own-domain model import
    from core.actor import Actor

    o1, o2 = market.complete(market.place()), market.complete(market.place())
    review(market, o1, 1, "bad")
    rid = review(market, o2, 5, "great").json()["data"]["id"]
    bad_id = market.client().get(f"/api/v1/farmers/{market.farmer.id}/reviews").json()["data"][1]["id"]
    services.set_hidden(Actor.from_user(market.admin), bad_id, True, "Abusive")
    body = market.client().get(f"/api/v1/farmers/{market.farmer.id}/reviews").json()
    assert [x["id"] for x in body["data"]] == [rid] and body["summary"]["average_rating"] == 5.0


def test_only_admin_can_moderate(market):
    from apps.reviews import services
    from core.actor import Actor
    from core.errors import ForbiddenError

    order = market.complete(market.place())
    rid = review(market, order).json()["data"]["id"]
    with pytest.raises(ForbiddenError):
        services.set_hidden(Actor.from_user(market.farmer), rid, True)


def test_farmer_is_notified(market):
    from apps.notifications import selectors

    review(market, market.complete(market.place()), 4)
    assert "review_received" in {n.kind for n in selectors.list_for_recipient(market.farmer.id)}
