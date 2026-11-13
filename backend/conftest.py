import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def _fast_password_hasher(settings):
    # Tests only: skip slow PBKDF2 so the suite stays fast. Production keeps Django's default.
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture
def make_user(db):
    from apps.identity import services

    counter = {"n": 0}

    def _make(role="farmer", **kw):
        counter["n"] += 1
        data = dict(full_name=f"Demo {role}", password="Str0ng-Example-Pass", role=role,
                    email=f"{role}{counter['n']}@example.test")
        data.update(kw)
        if role == "admin":  # admins are never self-registered
            from apps.identity.models import User

            return User.objects.create_superuser(email=data["email"], password=data["password"], full_name=data["full_name"])
        return services.register_user(**data)

    return _make


@pytest.fixture
def auth_client(db):
    from django.conf import settings  # noqa: F401
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken

    def _client(user=None):
        client = APIClient()
        if user is not None:
            client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
        return client

    return _client


@pytest.fixture
def make_listing(db):
    """Create an active listing through the catalogue service for the given farmer."""
    from datetime import date

    from apps.catalogue import services
    from apps.catalogue.models import Category
    from core.actor import Actor

    def _make(farmer, **kw):
        data = dict(category_id=Category.objects.get(slug="tomatoes").id, produce_name="Tomatoes",
                    price_per_unit="85.00", quantity_unit="kg", county="Kiambu", harvest_date=date.today())
        data.update(kw)
        from decimal import Decimal
        data["price_per_unit"] = Decimal(str(data["price_per_unit"]))
        return services.create_listing(Actor.from_user(farmer), data)

    return _make
