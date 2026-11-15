import uuid

from django.db import models


class AuditLog(models.Model):
    """Append-only record of sensitive actions. Never stores passwords, tokens or payment data."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor_id = models.UUIDField(null=True, blank=True, db_index=True)
    action = models.CharField(max_length=60, db_index=True)  # e.g. user.suspended
    target_type = models.CharField(max_length=40)
    target_id = models.CharField(max_length=64, blank=True)
    detail = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
