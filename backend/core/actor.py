import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class Actor:
    """Who is performing an operation. Services take this instead of a User model."""

    id: uuid.UUID
    role: str

    @classmethod
    def from_user(cls, user) -> "Actor":
        return cls(id=user.id, role=user.role)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"
