from django.core.exceptions import ValidationError
from django.db.models import Count, QuerySet

from apps.issues.contracts import IssueView
from apps.issues.models import Issue
from core.dto import MappedQuery


def get_issue(issue_id) -> Issue | None:
    try:
        return Issue.objects.filter(pk=issue_id).first()
    except (ValueError, TypeError, ValidationError):
        return None


def list_for_order(order_id, reporter_id=None) -> QuerySet[Issue]:
    qs = Issue.objects.filter(order_id=order_id)
    return qs.filter(reporter_id=reporter_id) if reporter_id else qs


def to_view(issue: Issue) -> IssueView:
    return IssueView(issue.id, issue.order_id, issue.category, issue.description, issue.status, issue.resolution, issue.handled_by, issue.created_at, issue.updated_at)


def list_all(status: str = "") -> MappedQuery:
    qs = Issue.objects.all()
    return MappedQuery(qs.filter(status=status) if status else qs, to_view)


def stats() -> dict:
    counts = {row["status"]: row["n"] for row in Issue.objects.values("status").annotate(n=Count("id"))}
    return {"total": sum(counts.values()), "by_status": counts}

# Public contract of this module: the only names other domains may use (enforced by core/tests/test_boundaries.py).
__all__ = ['list_all', 'stats']
