from django.db import transaction

from apps.issues import selectors
from apps.issues.models import Issue, IssueCategory, IssueStatus
from apps.notifications.services import notify
from apps.orders import selectors as orders
from core.actor import Actor
from core.errors import ConflictError, ForbiddenError, InvalidInputError, NotFoundError

MAX_OPEN_PER_ORDER = 5
REPORTABLE = {"paid", "completed"}


def report_issue(actor: Actor, order_id, category: str, description: str) -> Issue:
    """The order's buyer or farmer reports a problem with a paid or completed order."""
    order = orders.get_order_snapshot(order_id)
    if order is None or actor.id not in (order.buyer_id, order.farmer_id):
        raise NotFoundError("Order not found.")
    if category not in IssueCategory.values:
        raise InvalidInputError("Unknown issue category.", "category")
    description = (description or "").strip()
    if len(description) < 10:
        raise InvalidInputError("Please describe the problem in at least 10 characters.", "description")
    if order.status not in REPORTABLE:
        raise ConflictError("Issues can only be reported on paid or completed orders.", code="ORDER_NOT_REPORTABLE")
    open_count = selectors.list_for_order(order.id, actor.id).filter(status__in=[IssueStatus.OPEN, IssueStatus.INVESTIGATING]).count()
    if open_count >= MAX_OPEN_PER_ORDER:
        raise ConflictError("Too many open issues for this order.", code="TOO_MANY_OPEN_ISSUES")
    return Issue.objects.create(order_id=order.id, reporter_id=actor.id, category=category, description=description)


def list_my_order_issues(actor: Actor, order_id):
    order = orders.get_order_snapshot(order_id)
    if order is None or not (actor.is_admin or actor.id in (order.buyer_id, order.farmer_id)):
        raise NotFoundError("Order not found.")
    return selectors.list_for_order(order.id, None if actor.is_admin else actor.id)


@transaction.atomic
def update_issue(actor: Actor, issue_id, status: str, resolution: str = "") -> Issue:
    """Admin triage. Resolving or dismissing requires a resolution note and notifies the reporter."""
    if not actor.is_admin:
        raise ForbiddenError("Only an administrator can handle issues.")
    if status not in IssueStatus.values:
        raise InvalidInputError("Unknown issue status.", "status")
    visible = selectors.get_issue(issue_id)
    if visible is None:
        raise NotFoundError("Issue not found.")
    issue = Issue.objects.select_for_update().get(pk=visible.pk)
    resolution = (resolution or "").strip()
    if status in (IssueStatus.RESOLVED, IssueStatus.DISMISSED) and not resolution:
        raise InvalidInputError("A resolution note is required to close an issue.", "resolution")
    if issue.status in (IssueStatus.RESOLVED, IssueStatus.DISMISSED) and issue.status != status:
        raise ConflictError("A closed issue cannot be changed.", code="ISSUE_CLOSED")
    changed = (issue.status, issue.resolution) != (status, resolution or issue.resolution)
    issue.status, issue.handled_by = status, actor.id
    if resolution:
        issue.resolution = resolution
    issue.save()
    if changed:
        notify(issue.reporter_id, "issue_updated", "Issue update", f"Your issue is now {status}.", issue.order_id)
    return issue
