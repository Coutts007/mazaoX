from django.core.exceptions import ValidationError
from django.db.models import Avg, Count, QuerySet

from apps.reviews.contracts import ReviewView
from apps.reviews.models import Review
from core.dto import MappedQuery


def list_for_farmer(farmer_id) -> QuerySet[Review]:
    return Review.objects.filter(farmer_id=farmer_id, is_hidden=False)


def farmer_summary(farmer_id) -> dict:
    qs = list_for_farmer(farmer_id)
    agg = qs.aggregate(avg=Avg("rating"), count=Count("id"))
    distribution = {str(i): 0 for i in range(1, 6)}
    for row in qs.values("rating").annotate(n=Count("id")):
        distribution[str(row["rating"])] = row["n"]
    average = round(float(agg["avg"]), 2) if agg["avg"] is not None else None
    return {"average_rating": average, "review_count": agg["count"], "distribution": distribution}


def get_review(review_id) -> Review | None:
    try:
        return Review.objects.filter(pk=review_id).first()
    except (ValueError, TypeError, ValidationError):
        return None


def to_view(r: Review) -> ReviewView:
    return ReviewView(r.id, r.order_id, r.buyer_id, r.farmer_id, r.rating, r.comment, r.is_hidden, r.moderation_reason, r.created_at)


def list_all() -> MappedQuery:
    return MappedQuery(Review.objects.all(), to_view)


def stats() -> dict:
    return {"total": Review.objects.count(), "hidden": Review.objects.filter(is_hidden=True).count()}

# Public contract of this module: the only names other domains may use (enforced by core/tests/test_boundaries.py).
__all__ = ['list_all', 'stats']
