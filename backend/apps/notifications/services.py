"""Write interface of the notifications domain."""

import logging

from django.db import transaction
from django.utils import timezone

from apps.notifications import selectors
from apps.notifications.models import Notification
from core.actor import Actor
from core.errors import NotFoundError

logger = logging.getLogger(__name__)


def notify(recipient_id, kind: str, title: str, message: str, order_id=None) -> None:
    """Record a notification for a user. Never raises: a notification problem must not break the business action.

    The insert runs in a savepoint inside the caller's transaction, so it commits or rolls back together
    with the state change that caused it, but a failure here is contained and only logged.
    """
    try:
        with transaction.atomic():
            Notification.objects.create(
                recipient_id=recipient_id, kind=kind, title=title[:120], message=message[:255], order_id=order_id
            )
    except Exception:  # noqa: BLE001 - deliberately broad, see docstring
        logger.exception("Could not create %s notification", kind)


def mark_read(actor: Actor, notification_id) -> Notification:
    """Only the recipient can mark a notification read. Idempotent."""
    notification = selectors.get_for_recipient(notification_id, actor.id)
    if notification is None:
        raise NotFoundError("Notification not found.")
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=["is_read", "read_at"])
    return notification
