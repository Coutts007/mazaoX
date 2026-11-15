"""Read interface of the identity domain. Other domains must use these, never the model."""

import uuid

from django.db.models import Q

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


def get_display_names(user_ids) -> dict[str, str]:
    """Public-safe display names (first name only) for a batch of users, keyed by str(id)."""
    rows = User.objects.filter(pk__in=list(user_ids)).values_list("id", "full_name")
    return {str(pk): (name.split() or ["User"])[0] for pk, name in rows}


def search_users(q: str = "", role: str = "", is_active: bool | None = None):
    qs = User.objects.all().order_by("-date_joined", "-id")
    if q:
        qs = qs.filter(Q(email__icontains=q) | Q(phone__icontains=q) | Q(full_name__icontains=q))
    if role:
        qs = qs.filter(role=role)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    return qs


def stats() -> dict:
    from django.db.models import Count

    by_role = {r["role"]: r["n"] for r in User.objects.values("role").annotate(n=Count("id"))}
    return {"total": sum(by_role.values()), "by_role": by_role, "suspended": User.objects.filter(is_active=False).count()}
