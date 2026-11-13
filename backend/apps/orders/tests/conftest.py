from decimal import Decimal

import pytest

from apps.inventory import services as inventory
from core.actor import Actor


@pytest.fixture
def shop(make_user, make_listing, auth_client):
    """A farmer with two stocked listings (tomatoes 100 kg @ 85.00, onions 50 kg @ 60.50) and a buyer."""
    farmer, buyer = make_user("farmer"), make_user("buyer")
    tomatoes = make_listing(farmer, price_per_unit="85.00")
    onions = make_listing(farmer, produce_name="Onions", price_per_unit="60.50")
    actor = Actor.from_user(farmer)
    inventory.adjust_stock(actor, tomatoes.id, "addition", Decimal("100"))
    inventory.adjust_stock(actor, onions.id, "addition", Decimal("50"))
    return dict(farmer=farmer, buyer=buyer, tomatoes=tomatoes, onions=onions, client=auth_client,
                make_user=make_user, make_listing=make_listing, farmer_actor=actor)
