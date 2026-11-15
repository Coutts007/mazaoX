"""Data other domains may receive from catalogue. Plain immutable values, never model instances."""

import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class CategoryRef:
    id: uuid.UUID
    name: str
    slug: str


@dataclass(frozen=True)
class ImageRef:
    id: uuid.UUID
    width: int
    height: int
    position: int

    @property
    def url(self) -> str:
        return f"/api/v1/media/{self.id}"


@dataclass(frozen=True)
class ListingSummary:
    id: uuid.UUID
    farmer_id: uuid.UUID
    category: CategoryRef
    produce_name: str
    variety: str
    description: str
    declared_grade: str
    price_per_unit: Decimal
    quantity_unit: str
    county: str
    locality: str
    harvest_date: date | None
    status: str
    moderation_hidden: bool
    moderation_reason: str
    images: tuple[ImageRef, ...]
    created_at: datetime
    updated_at: datetime
    # Quality is the farmer's own claim; it is never independently verified here.
    grade_source: str = "farmer_declared"
    grade_verified: bool = False
