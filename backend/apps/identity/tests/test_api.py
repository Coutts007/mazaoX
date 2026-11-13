import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from apps.identity import services
from apps.identity.api.views import REFRESH_COOKIE

pytestmark = pytest.mark.django_db
PW = "Str0ng-Example-Pass"
REGISTER, LOGIN, ME = "/api/v1/auth/register", "/api/v1/auth/login", "/api/v1/auth/me"
REFRESH, LOGOUT = "/api/v1/auth/refresh", "/api/v1/auth/logout"


def payload(**kw):
    data = {"full_name": "Demo Farmer", "email": "farmer@example.test", "phone": "0700000000",
            "password": PW, "role": "farmer"}
    data.update(kw)
    return data


def login(client, identifier="farmer@example.test"):
    return client.post(LOGIN, {"identifier": identifier, "password": PW}, format="json")


def test_register_success_never_returns_password():
    r = APIClient().post(REGISTER, payload(), format="json")
    assert r.status_code == 201
    data = r.json()["data"]
    assert data["role"] == "farmer" and data["phone"] == "+254700000000"
    assert "password" not in data and PW not in r.content.decode()


@pytest.mark.parametrize(
    "override,field",
    [
        ({"password": "short"}, "password"),
        ({"password": "12345678"}, "password"),
        ({"role": "admin"}, "role"),
        ({"email": "not-an-email"}, "email"),
        ({"phone": "123"}, "phone"),
        ({"full_name": ""}, "full_name"),
    ],
)
def test_register_validation_errors(override, field):
    r = APIClient().post(REGISTER, payload(**override), format="json")
    assert r.status_code == 400
    err = r.json()["error"]
    assert err["code"] == "VALIDATION_ERROR"
    assert field in [d["field"] for d in err["details"]]


def test_register_requires_identifier():
    r = APIClient().post(REGISTER, payload(email="", phone=""), format="json")
    assert r.status_code == 400


def test_register_duplicate_email():
    c = APIClient()
    c.post(REGISTER, payload(), format="json")
    r = c.post(REGISTER, payload(phone=""), format="json")
    assert r.status_code == 400
    assert r.json()["error"]["details"][0]["field"] == "email"


def test_login_sets_httponly_refresh_cookie_and_returns_access():
    APIClient().post(REGISTER, payload(), format="json")
    c = APIClient()
    r = login(c, "0700000000")
    assert r.status_code == 200
    assert r.json()["data"]["access"]
    cookie = r.cookies[REFRESH_COOKIE]
    assert cookie["httponly"] and cookie["path"] == "/api/v1/auth"
    assert "refresh" not in r.json()["data"]


def test_login_wrong_password_generic_401():
    APIClient().post(REGISTER, payload(), format="json")
    r = APIClient().post(LOGIN, {"identifier": "farmer@example.test", "password": "nope"}, format="json")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHENTICATED"
    r2 = APIClient().post(LOGIN, {"identifier": "ghost@example.test", "password": "nope"}, format="json")
    assert r2.json()["error"]["message"] == r.json()["error"]["message"]


def test_suspended_user_cannot_login():
    user = services.register_user(full_name="X", password=PW, role="buyer", email="b@example.test")
    user.is_active = False
    user.save()
    r = login(APIClient(), "b@example.test")
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN"


def test_me_requires_authentication():
    r = APIClient().get(ME)
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHENTICATED"
    r = APIClient().get(ME, HTTP_AUTHORIZATION="Bearer garbage")
    assert r.status_code == 401
    assert "error" in r.json()


def test_me_returns_current_user():
    APIClient().post(REGISTER, payload(), format="json")
    c = APIClient()
    access = login(c).json()["data"]["access"]
    r = c.get(ME, HTTP_AUTHORIZATION=f"Bearer {access}")
    assert r.status_code == 200
    assert r.json()["data"]["email"] == "farmer@example.test"


def test_suspended_after_login_loses_access():
    user = services.register_user(full_name="X", password=PW, role="buyer", email="b@example.test")
    c = APIClient()
    access = login(c, "b@example.test").json()["data"]["access"]
    user.is_active = False
    user.save()
    assert c.get(ME, HTTP_AUTHORIZATION=f"Bearer {access}").status_code == 401


def test_refresh_rotates_and_old_token_is_rejected():
    APIClient().post(REGISTER, payload(), format="json")
    c = APIClient()
    login(c)
    old = c.cookies[REFRESH_COOKIE].value
    r = c.post(REFRESH)
    assert r.status_code == 200 and r.json()["data"]["access"]
    assert c.cookies[REFRESH_COOKIE].value != old
    replay = APIClient()
    replay.cookies[REFRESH_COOKIE] = old
    assert replay.post(REFRESH).status_code == 401


def test_refresh_without_cookie():
    assert APIClient().post(REFRESH).status_code == 401


def test_logout_blacklists_refresh_token():
    APIClient().post(REGISTER, payload(), format="json")
    c = APIClient()
    r = login(c)
    access = r.json()["data"]["access"]
    saved = c.cookies[REFRESH_COOKIE].value
    out = c.post(LOGOUT, HTTP_AUTHORIZATION=f"Bearer {access}")
    assert out.status_code == 204
    reuse = APIClient()
    reuse.cookies[REFRESH_COOKIE] = saved
    assert reuse.post(REFRESH).status_code == 401


def test_logout_requires_authentication():
    assert APIClient().post(LOGOUT).status_code == 401


@override_settings(REST_FRAMEWORK={
    **__import__("django.conf", fromlist=["settings"]).settings.REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {"auth": "3/min"},
})
def test_login_is_rate_limited():
    from rest_framework.throttling import ScopedRateThrottle
    ScopedRateThrottle.THROTTLE_RATES = {"auth": "3/min"}
    try:
        c = APIClient()
        codes = [c.post(LOGIN, {"identifier": "a@example.test", "password": "x"}, format="json").status_code for _ in range(5)]
    finally:
        from django.conf import settings
        ScopedRateThrottle.THROTTLE_RATES = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    assert codes[-1] == 429
