import uuid

from django.conf import settings
from django.db import models


class Profile(models.Model):
    """Profile details of one account. Created lazily on first access."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Identity's User is the only permitted cross-domain FK target (ADR-002).
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    county = models.CharField(max_length=40, blank=True)
    locality = models.CharField(max_length=100, blank=True)
    farm_name = models.CharField(max_length=150, blank=True)
    bio = models.TextField(max_length=1000, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile<{self.user_id}>"
