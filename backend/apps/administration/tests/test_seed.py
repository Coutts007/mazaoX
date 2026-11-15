import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.catalogue import selectors as catalogue
from apps.identity import selectors as identity

pytestmark = pytest.mark.django_db


def test_seed_demo_creates_a_usable_marketplace(settings, capsys):
    settings.PAYMENT_SIMULATION_ENABLED, settings.DEBUG = True, True
    call_command("seed_demo")
    stats = identity.stats()
    assert stats["by_role"] == {"admin": 1, "farmer": 3, "buyer": 2}
    assert catalogue.stats()["active_visible"] >= 5
    from apps.orders import selectors as orders
    s = orders.stats()
    assert s["by_status"] == {"completed": 1, "pending_payment": 1}
    from rest_framework.test import APIClient
    login = APIClient().post("/api/v1/auth/login", {"identifier": "achieng.buyer@example.test", "password": "Demo-Pass-12345"}, format="json")
    assert login.status_code == 200
    assert APIClient().get("/api/v1/listings").json()["pagination"]["total_items"] >= 5


def test_seed_demo_is_idempotent(settings):
    settings.PAYMENT_SIMULATION_ENABLED, settings.DEBUG = True, True
    call_command("seed_demo")
    before = identity.stats()["total"]
    call_command("seed_demo")
    assert identity.stats()["total"] == before


def test_seed_demo_refuses_outside_debug(settings):
    settings.DEBUG = False
    with pytest.raises(CommandError):
        call_command("seed_demo")
    assert identity.stats()["total"] == 0
