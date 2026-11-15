from django.core.exceptions import ValidationError
from django.db.models import QuerySet

from apps.quality.models import Inspection


def list_published_for_listing(listing_id) -> QuerySet[Inspection]:
    return Inspection.objects.filter(listing_id=listing_id, is_published=True)


def list_all_for_listing(listing_id) -> QuerySet[Inspection]:
    return Inspection.objects.filter(listing_id=listing_id)


def get_inspection(inspection_id) -> Inspection | None:
    try:
        return Inspection.objects.filter(pk=inspection_id).first()
    except (ValueError, TypeError, ValidationError):
        return None


def stats() -> dict:
    return {"total": Inspection.objects.count(), "published": Inspection.objects.filter(is_published=True).count()}
