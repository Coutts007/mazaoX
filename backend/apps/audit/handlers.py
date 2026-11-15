"""Turns domain events into audit entries (written inside the publisher's transaction)."""

from apps.audit.services import record
from core import events


def on_user_status_changed(actor_id, user_id, active, reason, listings_affected):
    record(actor_id, "user.reinstated" if active else "user.suspended", "user", user_id, {"reason": reason, "listings_affected": listings_affected})


def on_listing_moderated(actor_id, listing_id, hidden, reason):
    record(actor_id, "listing.hidden" if hidden else "listing.restored", "listing", listing_id, {"reason": reason})


def on_issue_triaged(actor_id, issue_id, status):
    record(actor_id, "issue.updated", "issue", issue_id, {"status": status})


def on_review_moderated(actor_id, review_id, hidden, reason):
    record(actor_id, "review.hidden" if hidden else "review.restored", "review", review_id, {"reason": reason})


def on_inspection_created(actor_id, inspection_id, listing_id, result):
    record(actor_id, "inspection.created", "inspection", inspection_id, {"listing_id": listing_id, "result": result})


def on_inspection_corrected(actor_id, inspection_id, fields, reason):
    record(actor_id, "inspection.corrected", "inspection", inspection_id, {"fields": fields, "reason": reason})


def register() -> None:
    events.subscribe("user.status_changed", on_user_status_changed)
    events.subscribe("listing.moderated", on_listing_moderated)
    events.subscribe("issue.triaged", on_issue_triaged)
    events.subscribe("review.moderated", on_review_moderated)
    events.subscribe("inspection.created", on_inspection_created)
    events.subscribe("inspection.corrected", on_inspection_corrected)
