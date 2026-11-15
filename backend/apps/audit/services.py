import logging

from apps.audit.models import AuditLog

logger = logging.getLogger(__name__)
_FORBIDDEN_KEYS = {"password", "token", "access", "refresh", "pin", "secret", "card"}


def record(actor_id, action: str, target_type: str, target_id="", detail: dict | None = None) -> AuditLog:
    """Write an audit entry inside the caller's transaction (so it exists iff the action committed)."""
    clean = {k: v for k, v in (detail or {}).items() if k.lower() not in _FORBIDDEN_KEYS}
    return AuditLog.objects.create(actor_id=actor_id, action=action, target_type=target_type, target_id=str(target_id), detail=clean)

# Public contract of this module: the only names other domains may use (enforced by core/tests/test_boundaries.py).
__all__ = ['record']
