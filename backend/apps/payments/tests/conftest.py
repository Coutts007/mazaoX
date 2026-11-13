from decimal import Decimal

import pytest

from apps.inventory import services as inventory
from apps.orders import services as order_services
from core.actor import Actor


@pytest.fixture(autouse=True)
def _simulation_on(settings):
    settings.PAYMENT_SIMULATION_ENABLED = True


@pytest.fixture
def shop(make_user, make_listing, auth_client):
    farmer, buyer = make_user("farmer"), make_user("buyer")
    listing = make_listing(farmer, price_per_unit="85.00")
    inventory.adjust_stock(Actor.from_user(farmer), listing.id, "addition", Decimal("100"))

    def place(qty="10", user=None):
        order, _ = order_services.create_order(
            Actor.from_user(user or buyer),
            items=[{"listing_id": listing.id, "quantity": Decimal(qty), "quantity_unit": "kg"}],
            delivery_method="collection",
        )
        return order

    return dict(farmer=farmer, buyer=buyer, listing=listing, place=place, client=auth_client, make_user=make_user)
