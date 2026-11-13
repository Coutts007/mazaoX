from django.core.exceptions import ValidationError
from django.db.models import QuerySet

from apps.notifications.models import Notification


def list_for_recipient(recipient_id, unread_only: bool = False) -> QuerySet[Notification]:
    qs = Notification.objects.filter(recipient_id=recipient_id)
    return qs.filter(is_read=False) if unread_only else qs


def unread_count(recipient_id) -> int:
    return Notification.objects.filter(recipient_id=recipient_id, is_read=False).count()


def get_for_recipient(notification_id, recipient_id) -> Notification | None:
    try:
        return Notification.objects.filter(pk=notification_id, recipient_id=recipient_id).first()
    except (ValueError, TypeError, ValidationError):
        return None
