"""In-process domain event bus (ADR-004).

A domain announces a business fact with `publish(name, **payload)`; other domains react by registering a
handler with `subscribe(name, handler)` (in their `AppConfig.ready()`). The publisher no longer knows who
reacts, so notifications and audit stay out of the business domains' imports.

Semantics, deliberately simple:
- Handlers run synchronously, in the publisher's database transaction, so a reaction commits or rolls back
  together with the action that caused it (an audit entry exists iff the action committed).
- Payloads are primitives only (strings, numbers, bools, lists, dicts): never model instances.
- A handler may raise; the exception reaches the publisher unless the handler contains it itself
  (notification handlers do, so a notification problem never breaks the business action).
- This is not a message broker and not an outbox: nothing is persisted or retried. Revisit if asynchronous
  fan-out (email/SMS) is added.

EVENT CATALOGUE (name: payload keys)
  order.placed          order_id, buyer_id, farmer_id, label, ttl_minutes
  order.cancelled       order_id, buyer_id, farmer_id, label, cancelled_by
  order.expired         order_id, buyer_id, label
  order.paid            order_id, buyer_id, farmer_id, label
  payment.failed        order_id, buyer_id
  review.created        order_id, farmer_id, rating
  issue.updated         order_id, reporter_id, status
  demand.matched        farmer_id, produce_name, quantity, quantity_unit, county
  delivery.status_changed  order_id, buyer_id, status
  user.status_changed   actor_id, user_id, active, reason, listings_affected
  listing.moderated     actor_id, listing_id, hidden, reason
  issue.triaged         actor_id, issue_id, status
  review.moderated      actor_id, review_id, hidden, reason
  inspection.created    actor_id, inspection_id, listing_id, result
  inspection.corrected  actor_id, inspection_id, fields, reason
"""

from collections import defaultdict
from collections.abc import Callable

_subscribers: dict[str, list[Callable[..., None]]] = defaultdict(list)


def subscribe(name: str, handler: Callable[..., None]) -> None:
    if handler not in _subscribers[name]:  # AppConfig.ready() may run more than once in tests
        _subscribers[name].append(handler)


def publish(name: str, **payload) -> None:
    for handler in list(_subscribers.get(name, ())):
        handler(**payload)
