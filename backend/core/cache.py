"""Redis-backed caching helpers. Every helper fails open: a cache outage must never break the API."""

import functools
import hashlib
import logging

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from rest_framework.response import Response

logger = logging.getLogger(__name__)


def _version(namespace: str) -> int:
    try:
        return cache.get(f"ns:{namespace}", 1)
    except Exception:  # noqa: BLE001 - fail open
        logger.warning("cache unavailable (version read)")
        return 1


def invalidate(namespace: str) -> None:
    """Invalidate every cached response of a namespace once the surrounding transaction commits.

    Bumping a version number makes all old keys unreachable at once (they expire on their own TTL).
    Running after commit guarantees a concurrent reader cannot re-cache pre-commit data under the new version.
    """
    def bump():
        try:
            try:
                cache.incr(f"ns:{namespace}")
            except ValueError:
                cache.set(f"ns:{namespace}", 2, None)
        except Exception:  # noqa: BLE001 - fail open
            logger.warning("cache unavailable (invalidate %s)", namespace)

    transaction.on_commit(bump)


def public_cache(namespace: str, ttl: int):
    """Cache a view's successful ANONYMOUS GET response. Authenticated requests always bypass the cache."""

    def decorator(method):
        @functools.wraps(method)
        def wrapper(self, request, *args, **kwargs):
            if not settings.PUBLIC_CACHE_ENABLED or request.META.get("HTTP_AUTHORIZATION"):
                return method(self, request, *args, **kwargs)
            raw = f"{request.path}?{'&'.join(sorted(request.META.get('QUERY_STRING', '').split('&')))}"
            key = f"pub:{namespace}:{_version(namespace)}:{hashlib.sha256(raw.encode()).hexdigest()}"
            try:
                hit = cache.get(key)
            except Exception:  # noqa: BLE001 - fail open
                hit = None
            if hit is not None:
                response = Response(hit)
                response["X-Cache"] = "HIT"
                return response
            response = method(self, request, *args, **kwargs)
            if response.status_code == 200:
                try:
                    cache.set(key, response.data, ttl)
                except Exception:  # noqa: BLE001 - fail open
                    logger.warning("cache unavailable (store)")
                response["X-Cache"] = "MISS"
            return response

        return wrapper

    return decorator


def cache_status() -> str:
    """'redis', 'local' or 'down' for the health endpoint."""
    try:
        cache.set("health:probe", "1", 5)
        ok = cache.get("health:probe") == "1"
    except Exception:  # noqa: BLE001
        return "down"
    if not ok:
        return "down"
    return "redis" if settings.REDIS_URL else "local"
