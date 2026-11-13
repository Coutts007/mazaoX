"""Write interface of the catalogue domain."""

from datetime import date

from django.db import transaction

from apps.catalogue import selectors
from apps.catalogue.models import Category, Listing, ListingStatus
from core.actor import Actor
from core.errors import ForbiddenError, InvalidInputError, NotFoundError
from core.kenya import canonical_county

EDITABLE = {
    "category_id", "produce_name", "variety", "description", "declared_grade",
    "price_per_unit", "quantity_unit", "county", "locality", "harvest_date",
}


def _clean(data: dict) -> dict:
    data = dict(data)
    if "county" in data:
        county = canonical_county(data["county"])
        if county is None:
            raise InvalidInputError("Enter a valid Kenyan county.", "county")
        data["county"] = county
    if "price_per_unit" in data and data["price_per_unit"] <= 0:
        raise InvalidInputError("Price must be greater than zero.", "price_per_unit")
    if data.get("harvest_date") and data["harvest_date"] > date.today():
        raise InvalidInputError("Harvest date cannot be in the future.", "harvest_date")
    if "category_id" in data and not Category.objects.filter(pk=data["category_id"], is_active=True).exists():
        raise InvalidInputError("Category does not exist.", "category_id")
    return data


def create_listing(actor: Actor, data: dict) -> Listing:
    if actor.role != "farmer":
        raise ForbiddenError("Only farmers can create listings.")
    unknown = set(data) - EDITABLE
    if unknown:
        raise InvalidInputError("Field not accepted.", sorted(unknown)[0])
    return Listing.objects.create(farmer_id=actor.id, **_clean(data))


def _owned_listing(actor: Actor, listing_id) -> Listing:
    listing = selectors.get_listing(listing_id)
    # Non-owners get 404 for inactive listings they could not see anyway; active ones get 403.
    if listing is None or (listing.status != ListingStatus.ACTIVE and not (actor.is_admin or actor.id == listing.farmer_id)):
        raise NotFoundError("Listing not found.")
    if not (actor.is_admin or actor.id == listing.farmer_id):
        raise ForbiddenError("You can only change your own listings.")
    return listing


@transaction.atomic
def update_listing(actor: Actor, listing_id, data: dict) -> Listing:
    unknown = set(data) - EDITABLE
    if unknown:
        raise InvalidInputError("Field not editable.", sorted(unknown)[0])
    listing = _owned_listing(actor, listing_id)
    for field, value in _clean(data).items():
        setattr(listing, field, value)
    listing.save()
    return listing


@transaction.atomic
def deactivate_listing(actor: Actor, listing_id) -> Listing:
    listing = _owned_listing(actor, listing_id)
    if listing.status != ListingStatus.INACTIVE:
        listing.status = ListingStatus.INACTIVE
        listing.save(update_fields=["status", "updated_at"])
    return listing
