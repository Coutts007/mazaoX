"""Data other domains may receive from identity. Plain immutable values, never the User model."""

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class UserView:
    id: uuid.UUID
    full_name: str
    email: str | None
    phone: str | None
    role: str
    is_active: bool
    date_joined: datetime
