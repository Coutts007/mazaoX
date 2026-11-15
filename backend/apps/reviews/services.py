from django.db import IntegrityError, transaction

from apps.orders import selectors as orders
from apps.reviews import selectors
from apps.reviews.contracts import ReviewView
from apps.reviews.models import Review
from core import events
from core.actor import Actor
from core.cache import invalidate
from core.errors import ConflictError, ForbiddenError, InvalidInputError, NotFoundError


@transaction.atomic
def create_review(actor: Actor, order_id, rating: int, comment: str = "") -> Review:
    if actor.role != "buyer":
        raise ForbiddenError("Only the buyer can review an order.")
    if not 1 <= rating <= 5:
        raise InvalidInputError("Rating must be between 1 and 5.", "rating")
    order = orders.get_order_snapshot(order_id)
    if order is None or order.buyer_id != actor.id:
        raise NotFoundError("Order not found.")
    if order.status != "completed":
        raise ConflictError("Only a completed order can be reviewed.", code="ORDER_NOT_COMPLETED")
    try:
        with transaction.atomic():
            review = Review.objects.create(
                order_id=order.id, buyer_id=actor.id, farmer_id=order.farmer_id, rating=rating, comment=(comment or "").strip()
            )
    except IntegrityError as exc:
        raise ConflictError("This order has already been reviewed.", code="REVIEW_EXISTS") from exc
    invalidate("reviews")
    events.publish("review.created", order_id=str(order.id), farmer_id=str(order.farmer_id), rating=rating)
    return review


@transaction.atomic
def set_hidden(actor: Actor, review_id, hidden: bool, reason: str = "") -> ReviewView:
    """Admin moderation. A hidden review is excluded from public lists and averages."""
    if not actor.is_admin:
        raise ForbiddenError("Only an administrator can moderate reviews.")
    review = selectors.get_review(review_id)
    if review is None:
        raise NotFoundError("Review not found.")
    review.is_hidden = hidden
    review.moderation_reason = (reason or "").strip()[:255] if hidden else ""
    review.save(update_fields=["is_hidden", "moderation_reason"])
    invalidate("reviews")
    return selectors.to_view(review)

# Public contract of this module: the only names other domains may use (enforced by core/tests/test_boundaries.py).
__all__ = ['create_review', 'set_hidden']
