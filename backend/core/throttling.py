"""DRF throttles that fail open if the shared cache (Redis) is unreachable."""

import logging

from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle, UserRateThrottle

logger = logging.getLogger(__name__)


class _FailOpen:
    def allow_request(self, request, view):
        try:
            return super().allow_request(request, view)
        except Exception:  # noqa: BLE001
            logger.warning("throttle cache unavailable; allowing request")
            return True


class SafeAnonRateThrottle(_FailOpen, AnonRateThrottle):
    pass


class SafeUserRateThrottle(_FailOpen, UserRateThrottle):
    pass


class SafeScopedRateThrottle(_FailOpen, ScopedRateThrottle):
    pass
