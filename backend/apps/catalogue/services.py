"""Write interface of the catalogue domain."""

from datetime import date

import logging
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction

from apps.catalogue import selectors
from apps.catalogue import media
from apps.catalogue.models import Category, Listing, ListingMedia, ListingStatus
from core.actor import Actor
from core.cache import invalidate
from core.errors import ConflictError, ForbiddenError, InvalidInputError, NotFoundError

logger = logging.getLogger(__name__)
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
    listing = Listing.objects.create(farmer_id=actor.id, **_clean(data))
    invalidate("catalogue")
    return listing


def _owned_listing(actor: Actor, listing_id) -> Listing:
    listing = selectors.get_listing(listing_id)
    # Non-owners get 404 for listings they could not see anyway; visible ones get 403.
    if listing is None or (not selectors._publicly_visible(listing) and not (actor.is_admin or actor.id == listing.farmer_id)):
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
    invalidate("catalogue")
    return listing


@transaction.atomic
def deactivate_listing(actor: Actor, listing_id) -> Listing:
    listing = _owned_listing(actor, listing_id)
    if listing.status != ListingStatus.INACTIVE:
        listing.status = ListingStatus.INACTIVE
        listing.save(update_fields=["status", "updated_at"])
        invalidate("catalogue")
    return listing


@transaction.atomic
def moderate_listing(actor: Actor, listing_id, hide: bool, reason: str = "") -> Listing:
    """Administrators hide or restore a listing. Hiding requires a reason."""
    if not actor.is_admin:
        raise ForbiddenError("Only an administrator can moderate listings.")
    reason = (reason or "").strip()
    if hide and not reason:
        raise InvalidInputError("A reason is required to hide a listing.", "reason")
    listing = selectors.get_listing(listing_id)
    if listing is None:
        raise NotFoundError("Listing not found.")
    listing.moderation_hidden = hide
    listing.moderation_reason = reason[:255] if hide else ""
    listing.save(update_fields=["moderation_hidden", "moderation_reason", "updated_at"])
    invalidate("catalogue")
    return listing


def set_owner_suspended(farmer_id, suspended: bool) -> int:
    """Called when a farmer account is suspended or reinstated: hides/shows all their listings."""
    count = Listing.objects.filter(farmer_id=farmer_id).update(owner_suspended=suspended)
    invalidate("catalogue")
    return count


@transaction.atomic
def activate_listing(actor: Actor, listing_id) -> Listing:
    """Re-list a deactivated listing. A listing hidden by an administrator stays hidden."""
    listing = _owned_listing(actor, listing_id)
    if listing.status != ListingStatus.ACTIVE:
        listing.status = ListingStatus.ACTIVE
        listing.save(update_fields=["status", "updated_at"])
        invalidate("catalogue")
    return listing


def add_media(actor: Actor, listing_id, uploaded) -> ListingMedia:
    """Owning farmer uploads a photo. Validated and re-encoded; the stored name is generated."""
    if actor.role != "farmer":
        raise ForbiddenError("Only the owning farmer can upload photos.")
    listing = selectors.get_listing(listing_id)
    if listing is None or listing.farmer_id != actor.id:
        raise NotFoundError("Listing not found.")
    if listing.media.count() >= settings.MEDIA_MAX_PER_LISTING:
        raise ConflictError(f"A listing can have at most {settings.MEDIA_MAX_PER_LISTING} photos.", "image", "TOO_MANY_PHOTOS")
    clean = media.sanitise(uploaded)
    name = default_storage.save(f"listings/{listing.id}/{uuid.uuid4().hex}.{clean.extension}", ContentFile(clean.data))
    try:
        created = ListingMedia.objects.create(
            listing=listing, storage_name=name, content_type=clean.content_type, size_bytes=len(clean.data),
            width=clean.width, height=clean.height, position=listing.media.count(),
        )
        invalidate("catalogue")
        return created
    except Exception:
        default_storage.delete(name)  # never leave an orphan file behind
        raise


@transaction.atomic
def remove_media(actor: Actor, listing_id, media_id) -> None:
    listing = _owned_listing(actor, listing_id)
    try:
        item = listing.media.get(pk=media_id)
    except (ListingMedia.DoesNotExist, ValueError, ValidationError):
        raise NotFoundError("Photo not found.")
    name = item.storage_name
    item.delete()
    invalidate("catalogue")
    try:
        default_storage.delete(name)
    except Exception:  # noqa: BLE001 - a missing file must not fail the request
        logger.exception("Could not delete stored file %s", name)
