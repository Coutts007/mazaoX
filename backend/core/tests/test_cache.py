import os

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from core import cache as core_cache
from core.throttling import SafeAnonRateThrottle

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _cache_on(settings):
    settings.PUBLIC_CACHE_ENABLED = True


def test_categories_are_cached(market):
    c = APIClient()
    assert c.get("/api/v1/categories")["X-Cache"] == "MISS"
    assert c.get("/api/v1/categories")["X-Cache"] == "HIT"


def test_each_query_string_has_its_own_entry(market):
    c = APIClient()
    a = c.get("/api/v1/listings", {"q": "tomato"})
    b = c.get("/api/v1/listings", {"q": "zzz"})
    assert a["X-Cache"] == "MISS" and b["X-Cache"] == "MISS"
    assert len(a.json()["data"]) == 1 and b.json()["data"] == []
    assert c.get("/api/v1/listings", {"q": "tomato"})["X-Cache"] == "HIT"


def test_authenticated_requests_bypass_the_cache(market):
    anon = APIClient()
    anon.get("/api/v1/listings")
    assert anon.get("/api/v1/listings")["X-Cache"] == "HIT"
    r = market.client(market.buyer).get("/api/v1/listings")
    assert r.status_code == 200 and "X-Cache" not in r


def test_writes_invalidate_after_commit(market, django_capture_on_commit_callbacks):
    anon = APIClient()
    assert len(anon.get("/api/v1/listings").json()["data"]) == 1
    assert anon.get("/api/v1/listings")["X-Cache"] == "HIT"
    with django_capture_on_commit_callbacks(execute=True):
        assert market.client(market.farmer).post(f"/api/v1/listings/{market.listing.id}/deactivate").status_code == 200
    fresh = anon.get("/api/v1/listings")
    assert fresh["X-Cache"] == "MISS" and fresh.json()["data"] == []
    detail_url = f"/api/v1/listings/{market.listing.id}"
    assert anon.get(detail_url).status_code == 404  # errors are never cached
    with django_capture_on_commit_callbacks(execute=True):
        market.client(market.farmer).post(f"/api/v1/listings/{market.listing.id}/activate")
    assert anon.get(detail_url).status_code == 200


def test_suspension_invalidates_public_farmer_pages(market, django_capture_on_commit_callbacks):
    anon = APIClient()
    url = f"/api/v1/farmers/{market.farmer.id}"
    assert anon.get(url).status_code == 200 and anon.get(url)["X-Cache"] == "HIT"
    with django_capture_on_commit_callbacks(execute=True):
        market.client(market.admin).patch(f"/api/v1/admin/users/{market.farmer.id}/status", {"is_active": False, "reason": "test"}, format="json")
    assert anon.get(url).status_code == 404


def test_review_changes_invalidate_review_pages(market, django_capture_on_commit_callbacks):
    anon = APIClient()
    url = f"/api/v1/farmers/{market.farmer.id}/reviews"
    order = market.complete(market.place())
    assert anon.get(url).json()["summary"]["review_count"] == 0
    with django_capture_on_commit_callbacks(execute=True):
        market.client(market.buyer).post(f"/api/v1/orders/{order.id}/reviews", {"rating": 4}, format="json")
    assert anon.get(url).json()["summary"]["review_count"] == 1


def test_cache_outage_fails_open(market, monkeypatch):
    def boom(*a, **k):
        raise ConnectionError("redis down")

    monkeypatch.setattr(cache, "get", boom)
    monkeypatch.setattr(cache, "set", boom)
    r = APIClient().get("/api/v1/listings")
    assert r.status_code == 200 and len(r.json()["data"]) == 1
    assert core_cache.cache_status() == "down"
    assert SafeAnonRateThrottle().allow_request(type("R", (), {"META": {}, "user": None})(), None) in (True, False)


def test_throttle_fails_open_when_cache_is_down(market, monkeypatch):
    monkeypatch.setattr(cache, "get", lambda *a, **k: (_ for _ in ()).throw(ConnectionError("down")))
    monkeypatch.setattr(cache, "set", lambda *a, **k: (_ for _ in ()).throw(ConnectionError("down")))
    r = APIClient().post("/api/v1/auth/login", {"identifier": "x@example.test", "password": "nope"}, format="json")
    assert r.status_code == 401  # not 500


def test_default_anonymous_rate_limit(market, settings):
    from rest_framework.settings import api_settings  # noqa: F401

    SafeAnonRateThrottle.THROTTLE_RATES = {"anon": "3/min"}
    try:
        c = APIClient()
        codes = [c.get("/api/v1/categories").status_code for _ in range(5)]
    finally:
        SafeAnonRateThrottle.THROTTLE_RATES = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    assert codes[:3] == [200, 200, 200] and codes[-1] == 429


@pytest.mark.skipif(not os.environ.get("REDIS_URL"), reason="needs a running Redis (REDIS_URL)")
def test_real_redis_backend_is_used():
    from django.conf import settings

    assert "redis" in settings.CACHES["default"]["BACKEND"].lower()
    assert core_cache.cache_status() == "redis"
    cache.set("probe", "x", 5)
    assert cache.get("probe") == "x"
