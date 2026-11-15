from decimal import Decimal

import pytest

from apps.audit import selectors as audit
from apps.notifications import selectors as notifications
from core import events
from core.dto import MappedQuery

pytestmark = pytest.mark.django_db


def test_publish_calls_every_subscriber_and_ignores_unknown_events():
    seen = []
    handler = lambda **p: seen.append(p)  # noqa: E731
    events.subscribe("test.something", handler)
    events.subscribe("test.something", handler)  # registering twice must not double-deliver
    events.publish("test.something", a=1)
    events.publish("test.nobody_listens", a=2)
    assert seen == [{"a": 1}]


def test_order_events_become_notifications_with_the_same_wording(market):
    events.publish("order.cancelled", order_id=str(market.listing.id), buyer_id=str(market.buyer.id),
                   farmer_id=str(market.farmer.id), label="order #abc", cancelled_by=str(market.buyer.id))
    assert [n.message for n in notifications.list_for_recipient(market.farmer.id)] == ["The order #abc was cancelled."]
    assert list(notifications.list_for_recipient(market.buyer.id)) == []  # the actor is not told about their own action


def test_demand_event_formats_quantity_in_the_notification(market):
    events.publish("demand.matched", farmer_id=str(market.farmer.id), produce_name="Tomatoes",
                   quantity=str(Decimal("50.000")), quantity_unit="kg", county="Kiambu")
    assert [n.message for n in notifications.list_for_recipient(market.farmer.id)] == [
        "A buyer is looking for 50 kg of Tomatoes in Kiambu."]


def test_audit_events_are_recorded_with_the_same_actions(market):
    events.publish("listing.moderated", actor_id=str(market.admin.id), listing_id=str(market.listing.id), hidden=True, reason="spam")
    (entry,) = list(audit.search(action="listing.hidden"))
    assert entry.target_type == "listing" and entry.detail == {"reason": "spam"}


def test_mapped_query_counts_and_slices_in_the_database(django_assert_num_queries):
    from apps.identity import selectors as identity

    users = identity.search_users()
    with django_assert_num_queries(1):
        total = users.count()
    assert total == len(users)
    page = users[0:2]
    assert isinstance(page, list) and all(hasattr(u, "email") and not hasattr(u, "save") for u in page)


def test_mapped_query_is_ordered_for_paginators():
    assert MappedQuery([], lambda x: x).ordered is True
