import uuid
from dataclasses import dataclass

from apps.identity import selectors as identity
from apps.profiles.models import Profile


@dataclass(frozen=True)
class PublicFarmer:
    id: uuid.UUID
    full_name: str
    farm_name: str
    county: str
    locality: str
    bio: str
    member_since: object


def get_profile(user_id) -> Profile | None:
    return Profile.objects.filter(user_id=user_id).first()


def get_public_farmer(farmer_id) -> PublicFarmer | None:
    """Public view of an active farmer. Never exposes email or phone."""
    user = identity.find_user(farmer_id)
    if user is None or user.role != "farmer" or not user.is_active:
        return None
    profile = get_profile(user.id)
    return PublicFarmer(
        id=user.id,
        full_name=user.full_name,
        farm_name=profile.farm_name if profile else "",
        county=profile.county if profile else "",
        locality=profile.locality if profile else "",
        bio=profile.bio if profile else "",
        member_since=user.date_joined,
    )

# Public contract of this module: the only names other domains may use (enforced by core/tests/test_boundaries.py).
__all__ = ['PublicFarmer', 'get_public_farmer']
