from django.core.exceptions import ValidationError
from django.db.models import Count, QuerySet

from apps.issues.models import Issue


def get_issue(issue_id) -> Issue | None:
    try:
        return Issue.objects.filter(pk=issue_id).first()
    except (ValueError, TypeError, ValidationError):
        return None


def list_for_order(order_id, reporter_id=None) -> QuerySet[Issue]:
    qs = Issue.objects.filter(order_id=order_id)
    return qs.filter(reporter_id=reporter_id) if reporter_id else qs


def list_all(status: str = "") -> QuerySet[Issue]:
    qs = Issue.objects.all()
    return qs.filter(status=status) if status else qs


def stats() -> dict:
    counts = {row["status"]: row["n"] for row in Issue.objects.values("status").annotate(n=Count("id"))}
    return {"total": sum(counts.values()), "by_status": counts}
