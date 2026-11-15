import uuid

from django.db import models
from django.db.models import Q


class Review(models.Model):
    """A buyer's review of a completed order (verified purchase). One per order."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_id = models.UUIDField(unique=True)
    buyer_id = models.UUIDField(db_index=True)
    farmer_id = models.UUIDField(db_index=True)
    rating = models.PositiveSmallIntegerField()
    comment = models.CharField(max_length=1000, blank=True)
    is_hidden = models.BooleanField(default=False)  # moderation
    moderation_reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [models.CheckConstraint(condition=Q(rating__gte=1, rating__lte=5), name="review_rating_1_to_5")]
