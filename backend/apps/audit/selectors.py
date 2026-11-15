from apps.audit.contracts import AuditEntry
from apps.audit.models import AuditLog
from core.dto import MappedQuery


def to_entry(log: AuditLog) -> AuditEntry:
    return AuditEntry(log.id, log.actor_id, log.action, log.target_type, log.target_id, log.detail, log.created_at)


def search(action: str = "", actor_id=None, target_type: str = "") -> MappedQuery:
    qs = AuditLog.objects.all()
    if action:
        qs = qs.filter(action=action)
    if actor_id:
        qs = qs.filter(actor_id=actor_id)
    if target_type:
        qs = qs.filter(target_type=target_type)
    return MappedQuery(qs, to_entry)

# Public contract of this module: the only names other domains may use (enforced by core/tests/test_boundaries.py).
__all__ = ['search']
