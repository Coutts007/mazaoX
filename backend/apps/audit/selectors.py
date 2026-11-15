from django.db.models import QuerySet

from apps.audit.models import AuditLog


def search(action: str = "", actor_id=None, target_type: str = "") -> QuerySet[AuditLog]:
    qs = AuditLog.objects.all()
    if action:
        qs = qs.filter(action=action)
    if actor_id:
        qs = qs.filter(actor_id=actor_id)
    if target_type:
        qs = qs.filter(target_type=target_type)
    return qs
