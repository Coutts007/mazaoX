import pytest
from django.db import connection
from rest_framework.test import APIClient

URL = "/api/v1/health"


@pytest.mark.django_db
def test_health_ok(settings):
    response = APIClient().get(URL)
    assert response.status_code == 200
    assert response.json() == {"data": {"status": "ok", "database": "up", "cache": "redis" if settings.REDIS_URL else "local"}}


def test_health_reports_database_down(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(connection, "cursor", boom)
    response = APIClient().get(URL)
    assert response.status_code == 503
    assert response.json()["data"]["status"] == "degraded" and response.json()["data"]["database"] == "down"
