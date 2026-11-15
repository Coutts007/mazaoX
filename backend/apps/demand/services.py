from datetime import date

from django.db import transaction

from apps.catalogue import selectors as catalogue
from apps.demand import selectors
from apps.demand.matching import find_matches
from apps.demand.models import DemandRequest, DemandStatus
from core import events
from core.actor import Actor
from core.errors import ConflictError, ForbiddenError, InvalidInputError, NotFoundError
from core.kenya import canonical_county

MAX_OPEN_PER_BUYER = 20
MAX_FARMERS_NOTIFIED = 20


def create_request(actor: Actor, data: dict) -> DemandRequest:
    if actor.role != "buyer":
        raise ForbiddenError("Only buyers can post demand requests.")
    county = canonical_county(data["county"])
    if county is None:
        raise InvalidInputError("Enter a valid Kenyan county.", "county")
    if data["quantity"] <= 0:
        raise InvalidInputError("Quantity must be greater than zero.", "quantity")
    if data["quantity_unit"] not in catalogue.quantity_units():
        raise InvalidInputError("Unknown quantity unit.", "quantity_unit")
    price = data.get("target_price_per_unit")
    if price is not None and price <= 0:
        raise InvalidInputError("Target price must be greater than zero.", "target_price_per_unit")
    if data["required_by"] < date.today():
        raise InvalidInputError("Required-by date cannot be in the past.", "required_by")
    if not data["produce_name"].strip():
        raise InvalidInputError("Produce name is required.", "produce_name")
    if selectors.list_for_actor(actor, DemandStatus.OPEN).count() >= MAX_OPEN_PER_BUYER:
        raise ConflictError("You have too many open demand requests. Close some first.", code="TOO_MANY_OPEN_REQUESTS")
    with transaction.atomic():
        request = DemandRequest.objects.create(
            buyer_id=actor.id, produce_name=data["produce_name"].strip(), quantity=data["quantity"], quantity_unit=data["quantity_unit"],
            target_price_per_unit=price, county=county, required_by=data["required_by"],
        )
        # Tell the farmers who already sell this produce. The message never names the buyer.
        farmers = list(dict.fromkeys(m.listing.farmer_id for m in find_matches(request)))[:MAX_FARMERS_NOTIFIED]
        for farmer_id in farmers:
            events.publish("demand.matched", farmer_id=str(farmer_id), produce_name=request.produce_name,
                           quantity=str(request.quantity), quantity_unit=request.quantity_unit, county=request.county)
    return request


@transaction.atomic
def close_request(actor: Actor, request_id) -> DemandRequest:
    visible = selectors.get_request_for_actor(request_id, actor)
    if visible is None:
        raise NotFoundError("Demand request not found.")
    request = DemandRequest.objects.select_for_update().get(pk=visible.pk)
    if request.status == DemandStatus.OPEN:
        request.status = DemandStatus.CLOSED
        request.save(update_fields=["status", "updated_at"])
    return request


def matches_for(actor: Actor, request_id):
    request = selectors.get_request_for_actor(request_id, actor)
    if request is None:
        raise NotFoundError("Demand request not found.")
    if request.status != DemandStatus.OPEN:
        raise ConflictError("Matches are only available for open requests.", code="REQUEST_NOT_OPEN")
    return request, find_matches(request)


def expire_overdue(today=None) -> int:
    today = today or date.today()
    return DemandRequest.objects.filter(status=DemandStatus.OPEN, required_by__lt=today).update(status=DemandStatus.EXPIRED)

# Public contract of this module: the only names other domains may use (enforced by core/tests/test_boundaries.py).
__all__ = ['create_request']
