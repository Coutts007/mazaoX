from datetime import date

from django.db import transaction

from apps.catalogue import selectors as catalogue
from apps.quality import selectors
from apps.quality.models import Inspection, InspectionResult, InspectionRevision
from core import events
from core.actor import Actor
from core.errors import ForbiddenError, InvalidInputError, NotFoundError

EDITABLE = {"inspected_on", "scope", "result", "assessed_grade", "notes", "is_published"}


def _require_admin(actor: Actor) -> None:
    if not actor.is_admin:
        raise ForbiddenError("Only an administrator can record inspections.")


def _validate(data: dict) -> None:
    if "inspected_on" in data and data["inspected_on"] > date.today():
        raise InvalidInputError("Inspection date cannot be in the future.", "inspected_on")
    if "scope" in data and not data["scope"].strip():
        raise InvalidInputError("The scope of the inspection is required.", "scope")
    if "result" in data and data["result"] not in InspectionResult.values:
        raise InvalidInputError("Unknown inspection result.", "result")


@transaction.atomic
def create_inspection(actor: Actor, listing_id, data: dict) -> Inspection:
    _require_admin(actor)
    if not catalogue.listing_exists(listing_id):
        raise NotFoundError("Listing not found.")
    missing = {"inspected_on", "scope", "result"} - set(data)
    if missing:
        raise InvalidInputError("This field is required.", sorted(missing)[0])
    unknown = set(data) - EDITABLE
    if unknown:
        raise InvalidInputError("Field not accepted.", sorted(unknown)[0])
    _validate(data)
    inspection = Inspection.objects.create(listing_id=listing_id, inspector_id=actor.id, **data)
    events.publish("inspection.created", actor_id=str(actor.id), inspection_id=str(inspection.id), listing_id=str(listing_id), result=inspection.result)
    return inspection


def _snapshot(i: Inspection) -> dict:
    return {
        "inspected_on": i.inspected_on.isoformat(), "scope": i.scope, "result": i.result,
        "assessed_grade": i.assessed_grade, "notes": i.notes, "is_published": i.is_published,
    }


@transaction.atomic
def correct_inspection(actor: Actor, inspection_id, data: dict, reason: str) -> Inspection:
    """Correct a record. The previous values are kept as a revision and the change is audited."""
    _require_admin(actor)
    reason = (reason or "").strip()
    if not reason:
        raise InvalidInputError("A reason is required to correct an inspection.", "reason")
    unknown = set(data) - EDITABLE
    if unknown:
        raise InvalidInputError("Field not editable.", sorted(unknown)[0])
    _validate(data)
    visible = selectors.get_inspection(inspection_id)
    if visible is None:
        raise NotFoundError("Inspection not found.")
    inspection = Inspection.objects.select_for_update().get(pk=visible.pk)
    InspectionRevision.objects.create(inspection=inspection, snapshot=_snapshot(inspection), changed_by=actor.id, reason=reason[:255])
    for field, value in data.items():
        setattr(inspection, field, value)
    inspection.save()
    events.publish("inspection.corrected", actor_id=str(actor.id), inspection_id=str(inspection.id), fields=sorted(data), reason=reason[:255])
    return inspection

# Public contract of this module: the only names other domains may use (enforced by core/tests/test_boundaries.py).
__all__ = ['create_inspection']
