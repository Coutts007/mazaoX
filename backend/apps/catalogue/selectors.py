"""Read interface of the catalogue domain."""

import uuid
from dataclasses import dataclass
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Q, QuerySet

from apps.catalogue.models import Category, Listing, ListingStatus
from core.actor import Actor


@dataclass(frozen=True)
class ListingSnapshot:
    """What other domains (orders, inventory) may know about a listing."""

    id: uuid.UUID
    farmer_id: uuid.UUID
    produce_name: str
    price_per_unit: Decimal
    quantity_unit: str
    is_active: bool


def list_categories() -> QuerySet[Category]:
    return Category.objects.filter(is_active=True)


def get_listing_snapshot(listing_id) -> ListingSnapshot | None:
    listing = _get(listing_id)
    if listing is None:
        return None
    return ListingSnapshot(
        id=listing.id,
        farmer_id=listing.farmer_id,
        produce_name=listing.produce_name,
        price_per_unit=listing.price_per_unit,
        quantity_unit=listing.quantity_unit,
        is_active=listing.status == ListingStatus.ACTIVE,
    )


def _get(listing_id) -> Listing | None:
    try:
        return Listing.objects.select_related("category").filter(pk=listing_id).first()
    except (ValueError, TypeError, ValidationError):  # malformed UUID
        return None


def get_visible_listing(listing_id, actor: Actor | None) -> Listing | None:
    """Active listings are public; owners and admins also see their inactive ones."""
    listing = _get(listing_id)
    if listing is None:
        return None
    if listing.status == ListingStatus.ACTIVE:
        return listing
    if actor and (actor.is_admin or actor.id == listing.farmer_id):
        return listing
    return None


def get_listing(listing_id) -> Listing | None:
    return _get(listing_id)


def search_listings(filters: dict, actor: Actor | None = None) -> QuerySet[Listing]:
    qs = Listing.objects.select_related("category")
    if filters.get("mine") and actor:
        qs = qs.filter(farmer_id=actor.id)
    else:
        qs = qs.filter(status=ListingStatus.ACTIVE, category__is_active=True)
    if q := filters.get("q"):
        qs = qs.filter(Q(produce_name__icontains=q) | Q(variety__icontains=q) | Q(description__icontains=q))
    if v := filters.get("category_id"):
        qs = qs.filter(category_id=v)
    if v := filters.get("county"):
        qs = qs.filter(county__iexact=v)
    if v := filters.get("locality"):
        qs = qs.filter(locality__icontains=v)
    if (v := filters.get("min_price")) is not None:
        qs = qs.filter(price_per_unit__gte=v)
    if (v := filters.get("max_price")) is not None:
        qs = qs.filter(price_per_unit__lte=v)
    if v := filters.get("quantity_unit"):
        qs = qs.filter(quantity_unit=v)
    if v := filters.get("declared_grade"):
        qs = qs.filter(declared_grade__icontains=v)
    return qs
