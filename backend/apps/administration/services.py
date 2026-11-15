"""Administrator operations. Each one delegates to the owning domain's service and writes an audit entry.

Administration owns no business data; it never bypasses a domain's rules.
"""

from django.db import transaction

from apps.audit.services import record
from apps.catalogue import selectors as catalogue_selectors
from apps.catalogue import services as catalogue
from apps.delivery import selectors as delivery_selectors
from apps.demand import selectors as demand_selectors
from apps.identity import selectors as identity_selectors
from apps.identity import services as identity
from apps.issues import selectors as issue_selectors
from apps.issues import services as issues
from apps.orders import selectors as order_selectors
from apps.payments import selectors as payment_selectors
from apps.quality import selectors as quality_selectors
from apps.reviews import selectors as review_selectors
from apps.reviews import services as reviews
from core.actor import Actor
from core.cache import invalidate
from core.errors import ForbiddenError, InvalidInputError, NotFoundError


def _require_admin(actor: Actor) -> None:
    if not actor.is_admin:
        raise ForbiddenError("Administrator access required.")


@transaction.atomic
def set_user_status(actor: Actor, user_id, active: bool, reason: str = ""):
    _require_admin(actor)
    reason = (reason or "").strip()
    if not active and not reason:
        raise InvalidInputError("A reason is required to suspend an account.", "reason")
    try:
        user = identity.set_user_active(actor.id, actor.is_admin, user_id, active)
    except identity.IdentityError as exc:
        if "not found" in exc.message.lower():
            raise NotFoundError(exc.message) from exc
        raise InvalidInputError(exc.message, exc.field or "user_id") from exc
    hidden = 0
    if user.role == "farmer":  # a suspended farmer's listings leave the marketplace; reinstating restores them
        hidden = catalogue.set_owner_suspended(user.id, not active)
    invalidate("profiles")
    invalidate("reviews")
    record(actor.id, "user.reinstated" if active else "user.suspended", "user", user.id, {"reason": reason[:255], "listings_affected": hidden})
    return user


@transaction.atomic
def moderate_listing(actor: Actor, listing_id, hidden: bool, reason: str = ""):
    _require_admin(actor)
    listing = catalogue.moderate_listing(actor, listing_id, hidden, reason)
    record(actor.id, "listing.hidden" if hidden else "listing.restored", "listing", listing.id, {"reason": (reason or "").strip()[:255]})
    return listing


@transaction.atomic
def update_issue(actor: Actor, issue_id, status: str, resolution: str = ""):
    _require_admin(actor)
    issue = issues.update_issue(actor, issue_id, status, resolution)
    record(actor.id, "issue.updated", "issue", issue.id, {"status": status})
    return issue


@transaction.atomic
def moderate_review(actor: Actor, review_id, hidden: bool, reason: str = ""):
    _require_admin(actor)
    review = reviews.set_hidden(actor, review_id, hidden, reason)
    record(actor.id, "review.hidden" if hidden else "review.restored", "review", review.id, {"reason": (reason or "").strip()[:255]})
    return review


def summary(actor: Actor) -> dict:
    _require_admin(actor)
    return {
        "users": identity_selectors.stats(),
        "listings": catalogue_selectors.stats(),
        "orders": order_selectors.stats(),
        "payments": payment_selectors.stats(),
        "deliveries": delivery_selectors.stats(),
        "issues": issue_selectors.stats(),
        "reviews": review_selectors.stats(),
        "inspections": quality_selectors.stats(),
        "demand_requests": demand_selectors.stats(),
    }
