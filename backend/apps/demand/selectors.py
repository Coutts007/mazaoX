from django.core.exceptions import ValidationError
from django.db.models import Count, QuerySet

from apps.demand.models import DemandRequest, DemandStatus
from core.actor import Actor


def get_request(request_id) -> DemandRequest | None:
    try:
        return DemandRequest.objects.filter(pk=request_id).first()
    except (ValueError, TypeError, ValidationError):
        return None


def get_request_for_actor(request_id, actor: Actor) -> DemandRequest | None:
    r = get_request(request_id)
    return r if r is not None and (actor.is_admin or r.buyer_id == actor.id) else None


def list_for_actor(actor: Actor, status: str = "") -> QuerySet[DemandRequest]:
    qs = DemandRequest.objects.all() if actor.is_admin else DemandRequest.objects.filter(buyer_id=actor.id)
    return qs.filter(status=status) if status else qs


def list_open_for_market(produce: str = "", county: str = "") -> QuerySet[DemandRequest]:
    qs = DemandRequest.objects.filter(status=DemandStatus.OPEN)
    if produce:
        qs = qs.filter(produce_name__icontains=produce)
    if county:
        qs = qs.filter(county__iexact=county)
    return qs.order_by("required_by", "-created_at")


def stats() -> dict:
    return {"by_status": {r["status"]: r["n"] for r in DemandRequest.objects.values("status").annotate(n=Count("id"))}}
