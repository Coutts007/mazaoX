"""Data other domains may receive from audit. Plain immutable values, never model instances."""

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AuditEntry:
    id: uuid.UUID
    actor_id: uuid.UUID | None
    action: str
    target_type: str
    target_id: str
    detail: dict
    created_at: datetime
