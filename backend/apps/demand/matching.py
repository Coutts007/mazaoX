"""Informational matching of a demand request against current public listings.

It reads catalogue and inventory through their selectors and writes nothing: no order, no reservation.
"""

from dataclasses import dataclass
from decimal import Decimal

from apps.catalogue import selectors as catalogue
from apps.catalogue.contracts import ListingSummary
from apps.demand.models import DemandRequest
from apps.inventory import selectors as inventory

MAX_CANDIDATES = 100
MAX_RESULTS = 20


@dataclass(frozen=True)
class Match:
    listing: ListingSummary
    score: int
    reasons: list
    available: Decimal


def find_matches(request: DemandRequest) -> list[Match]:
    candidates = catalogue.find_listings({"q": request.produce_name}, MAX_CANDIDATES)
    matches = []
    for listing in candidates:
        reasons, score = ["name"], 40
        if listing.quantity_unit == request.quantity_unit:
            reasons.append("unit")
            score += 20
        else:
            continue  # quantities in different units cannot be compared safely
        if listing.county.lower() == request.county.lower():
            reasons.append("county")
            score += 20
        if request.target_price_per_unit is not None and listing.price_per_unit <= request.target_price_per_unit:
            reasons.append("within_target_price")
            score += 10
        available = inventory.get_availability(listing.id, listing.quantity_unit).available
        if available >= request.quantity:
            reasons.append("enough_stock")
            score += 10
        elif available <= 0:
            continue  # nothing to buy
        matches.append(Match(listing, score, reasons, available))
    matches.sort(key=lambda m: (-m.score, m.listing.price_per_unit))
    return matches[:MAX_RESULTS]
