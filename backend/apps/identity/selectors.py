"""Read interface of the identity domain. Other domains must use these, never the model."""

import uuid

from django.core.exceptions import ValidationError

from apps.identity.models import User
from apps.identity.phone import normalise_phone


def get_user_by_id(user_id: uuid.UUID | str) -> User | None:
    try:
        return User.objects.filter(pk=user_id).first()
    except (ValueError, TypeError, ValidationError):
        return None


def get_user_by_identifier(identifier: str) -> User | None:
    """Find a user by email or Kenyan phone number."""
    identifier = (identifier or "").strip()
    if "@" in identifier:
        return User.objects.filter(email__iexact=identifier).first()
    phone = normalise_phone(identifier)
    return User.objects.filter(phone=phone).first() if phone else None


def email_exists(email: str) -> bool:
    return User.objects.filter(email__iexact=email).exists()


def phone_exists(phone: str) -> bool:
    return User.objects.filter(phone=phone).exists()
