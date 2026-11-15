"""Data other domains may receive from issues. Plain immutable values, never model instances."""

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class IssueView:
    id: uuid.UUID
    order_id: uuid.UUID
    category: str
    description: str
    status: str
    resolution: str
    handled_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
