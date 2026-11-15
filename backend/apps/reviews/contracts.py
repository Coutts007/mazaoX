"""Data other domains may receive from reviews. Plain immutable values, never model instances."""

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ReviewView:
    id: uuid.UUID
    order_id: uuid.UUID
    buyer_id: uuid.UUID
    farmer_id: uuid.UUID
    rating: int
    comment: str
    is_hidden: bool
    moderation_reason: str
    created_at: datetime
