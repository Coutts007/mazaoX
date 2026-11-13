from apps.identity import selectors as identity
from apps.profiles.models import Profile
from core.actor import Actor
from core.errors import InvalidInputError, NotFoundError
from core.kenya import canonical_county

EDITABLE = {"county", "locality", "farm_name", "bio"}


def get_or_create_profile(actor: Actor) -> Profile:
    profile, _ = Profile.objects.get_or_create(user_id=actor.id)
    return profile


def update_profile(actor: Actor, data: dict) -> Profile:
    unknown = set(data) - EDITABLE
    if unknown:
        raise InvalidInputError(f"Field not editable: {sorted(unknown)[0]}.", sorted(unknown)[0])
    if identity.get_user_by_id(actor.id) is None:
        raise NotFoundError("Account not found.")
    if "county" in data and data["county"]:
        county = canonical_county(data["county"])
        if county is None:
            raise InvalidInputError("Enter a valid Kenyan county.", "county")
        data = {**data, "county": county}
    if "farm_name" in data and data["farm_name"] and actor.role != "farmer":
        raise InvalidInputError("Only farmers have a farm name.", "farm_name")
    profile = get_or_create_profile(actor)
    for field, value in data.items():
        setattr(profile, field, value)
    profile.save()
    return profile
