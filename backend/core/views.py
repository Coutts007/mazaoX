import logging

from django.db import connection
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.cache import cache_status

logger = logging.getLogger(__name__)


class HealthView(APIView):
    """Liveness plus database connectivity check."""

    authentication_classes: list = []
    permission_classes: list = []

    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            db_up = True
        except Exception:  # noqa: BLE001 - any failure means the DB is unavailable
            logger.exception("Health check: database unavailable")
            db_up = False
        cache_state = cache_status()
        healthy = db_up and cache_state != "down"
        body = {"data": {"status": "ok" if healthy else "degraded", "database": "up" if db_up else "down", "cache": cache_state}}
        return Response(body, status=status.HTTP_200_OK if db_up else status.HTTP_503_SERVICE_UNAVAILABLE)
