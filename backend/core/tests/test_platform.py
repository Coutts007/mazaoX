import pytest
from django.core.checks import run_checks
from django.test import Client
from rest_framework.test import APIClient

ORIGIN = "http://localhost:5180"


def preflight(origin=ORIGIN, headers="authorization,content-type,idempotency-key", method="POST"):
    return Client().options(
        "/api/v1/orders", HTTP_ORIGIN=origin, HTTP_ACCESS_CONTROL_REQUEST_METHOD=method,
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS=headers,
    )


def test_cors_preflight_allows_frontend_with_credentials_and_idempotency_key():
    r = preflight()
    assert r.status_code == 200
    assert r["Access-Control-Allow-Origin"] == ORIGIN
    assert r["Access-Control-Allow-Credentials"] == "true"
    allowed = r["Access-Control-Allow-Headers"].lower()
    assert "idempotency-key" in allowed and "authorization" in allowed and "content-type" in allowed
    assert "POST" in r["Access-Control-Allow-Methods"] and "PATCH" in r["Access-Control-Allow-Methods"]


def test_cors_rejects_unknown_origin():
    assert "Access-Control-Allow-Origin" not in preflight("https://evil.example")


def test_cors_exposes_custom_headers_on_real_responses():
    r = Client().get("/api/v1/categories", HTTP_ORIGIN=ORIGIN)
    assert r["Access-Control-Allow-Origin"] == ORIGIN
    exposed = r["Access-Control-Expose-Headers"].lower()
    assert "idempotent-replay" in exposed and "x-request-id" in exposed


@pytest.mark.django_db
def test_request_id_generated_echoed_and_sanitised():
    c = APIClient()
    assert len(c.get("/api/v1/health")["X-Request-ID"]) == 32
    assert c.get("/api/v1/health", HTTP_X_REQUEST_ID="trace-12345678")["X-Request-ID"] == "trace-12345678"
    assert c.get("/api/v1/health", HTTP_X_REQUEST_ID="bad id\r\nX-Evil: 1")["X-Request-ID"] != "bad id"


@pytest.mark.django_db
def test_api_responses_are_not_cacheable_by_default_and_hardened():
    r = APIClient().get("/api/v1/health")
    assert r["Cache-Control"] == "no-store"
    assert r["X-Content-Type-Options"] == "nosniff" and r["X-Frame-Options"] == "DENY"
    assert r["Referrer-Policy"] == "same-origin"


@pytest.mark.django_db
def test_error_envelope_never_leaks_internals():
    r = APIClient().get("/api/v1/listings/not-a-uuid")
    body = r.content.decode()
    assert "Traceback" not in body and "django" not in body.lower()


def test_weak_secret_key_is_an_error_when_not_debug(settings):
    settings.DEBUG, settings.SECRET_KEY = False, "change-me"
    assert "mazaox.E001" in [m.id for m in run_checks()]
    settings.SECRET_KEY = "x" * 50
    assert "mazaox.E001" not in [m.id for m in run_checks()]


@pytest.mark.django_db
def test_openapi_schema_and_docs_are_served_and_cover_the_api():
    c = APIClient()
    r = c.get("/api/v1/schema?format=json")
    assert r.status_code == 200
    schema = r.json()
    assert schema["info"]["title"] == "MazaoX API"
    paths = set(schema["paths"])
    for expected in ["/api/v1/auth/login", "/api/v1/listings", "/api/v1/orders", "/api/v1/inventory/listings/{listing_id}",
                     "/api/v1/payments/simulations/{payment_id}/complete", "/api/v1/notifications", "/api/v1/demand-requests",
                     "/api/v1/admin/reports/summary", "/api/v1/inspections/{inspection_id}", "/api/v1/media/{media_id}"]:
        assert expected in paths, expected
    assert c.get("/api/v1/docs").status_code == 200


@pytest.mark.django_db
def test_static_admin_assets_are_served_by_whitenoise():
    assert Client().get("/admin/login/").status_code == 200


@pytest.mark.django_db
def test_openapi_documents_request_bodies_for_input_endpoints():
    schema = APIClient().get("/api/v1/schema?format=json").json()
    for path, method in [("/api/v1/auth/register", "post"), ("/api/v1/auth/login", "post"), ("/api/v1/listings", "post"),
                         ("/api/v1/orders", "post"), ("/api/v1/inventory/listings/{listing_id}/adjustments", "post"),
                         ("/api/v1/payments/simulations/{payment_id}/complete", "post"),
                         ("/api/v1/listings/{listing_id}/media", "post"), ("/api/v1/demand-requests", "post")]:
        assert "requestBody" in schema["paths"][path][method], (path, method)
    params = {p["name"] for p in schema["paths"]["/api/v1/listings"]["get"]["parameters"]}
    assert {"q", "county", "min_price", "min_quantity", "ordering"} <= params
