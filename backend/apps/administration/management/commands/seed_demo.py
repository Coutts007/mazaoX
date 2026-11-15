"""Load clearly-labelled SYNTHETIC demo data through the domain services (no direct table writes)."""

from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.catalogue import selectors as catalogue_selectors
from apps.catalogue import services as catalogue
from apps.delivery import services as delivery
from apps.demand import services as demand
from apps.identity import selectors as identity_selectors
from apps.identity import services as identity
from apps.inventory import services as inventory
from apps.orders import services as orders
from apps.payments import services as payments
from apps.quality import services as quality
from apps.reviews import services as reviews
from core.actor import Actor

FARMERS = [
    ("Wanjiru Demo", "wanjiru.farmer@example.test", "Kiambu", "Limuru"),
    ("Kipchoge Demo", "kipchoge.farmer@example.test", "Nakuru", "Njoro"),
    ("Mwangi Demo", "mwangi.farmer@example.test", "Meru", "Imenti"),
]
BUYERS = [("Achieng Demo", "achieng.buyer@example.test"), ("Otieno Demo", "otieno.buyer@example.test")]
PRODUCE = [  # category slug, name, unit, price, stock
    ("tomatoes", "Roma Tomatoes", "kg", "85.00", "500"),
    ("potatoes", "Shangi Potatoes", "kg", "45.00", "1200"),
    ("onions", "Red Onions", "bag", "2500.00", "40"),
    ("kale", "Sukuma Wiki (Kale)", "kg", "30.00", "300"),
    ("maize", "Dry Maize", "bag", "3200.00", "60"),
]


class Command(BaseCommand):
    help = "Create synthetic demo users, listings, stock, orders, a review, an inspection and a demand request."

    def add_arguments(self, parser):
        parser.add_argument("--password", default="Demo-Pass-12345", help="password for every demo account")
        parser.add_argument("--force", action="store_true", help="allow running when DEBUG is off")

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError("Refusing to seed demo data while DEBUG is off (use --force if you really mean it).")
        if identity_selectors.get_user_by_identifier(FARMERS[0][1]):
            self.stdout.write("Demo data already present; nothing to do.")
            return
        pw = options["password"]
        categories = {c.slug: c for c in catalogue_selectors.list_categories()}

        admin = identity.create_admin(email="admin.demo@example.test", password=pw, full_name="Admin Demo")
        farmers = [identity.register_user(full_name=n, email=e, password=pw, role="farmer") for n, e, _, _ in FARMERS]
        buyers = [identity.register_user(full_name=n, email=e, password=pw, role="buyer") for n, e in BUYERS]
        admin_actor = Actor.from_user(admin)

        listings = []
        for i, (farmer, (_, _, county, locality)) in enumerate(zip(farmers, FARMERS)):
            actor = Actor.from_user(farmer)
            for slug, name, unit, price, stock in PRODUCE[i::len(farmers)] + PRODUCE[:1]:
                listing = catalogue.create_listing(actor, {
                    "category_id": categories[slug].id, "produce_name": name, "price_per_unit": Decimal(price), "quantity_unit": unit,
                    "county": county, "locality": locality, "declared_grade": "Farmer-declared Grade A",
                    "description": "Synthetic demo listing.", "harvest_date": date.today() - timedelta(days=2),
                })
                inventory.adjust_stock(actor, listing.id, "addition", Decimal(stock), "Demo stock")
                listings.append(listing)

        # one finished trade (order -> paid -> delivered -> reviewed) and one open order
        buyer = Actor.from_user(buyers[0])
        first = listings[0]
        done, _ = orders.create_order(buyer, items=[{"listing_id": first.id, "quantity": Decimal("20"), "quantity_unit": first.quantity_unit}], delivery_method="collection")
        attempt, _ = payments.start_simulated_payment(buyer, done.id)
        if settings.PAYMENT_SIMULATION_ENABLED:
            payments.complete_simulated_payment(buyer, attempt.id, "success")
            record = delivery.create_delivery(admin_actor, done.id)
            delivery.update_status(admin_actor, record.id, "dispatched")
            delivery.update_status(admin_actor, record.id, "delivered")
            reviews.create_review(buyer, done.id, 5, "Fresh produce, demo review.")
        orders.create_order(Actor.from_user(buyers[1]), items=[{"listing_id": listings[1].id, "quantity": Decimal("10"), "quantity_unit": listings[1].quantity_unit}], delivery_method="delivery", delivery_location="Demo delivery point")

        quality.create_inspection(admin_actor, first.id, {"inspected_on": date.today(), "scope": "Demo batch, synthetic record", "result": "passed", "assessed_grade": "Grade A"})
        demand.create_request(buyer, {"produce_name": "Potatoes", "quantity": Decimal("200"), "quantity_unit": "kg", "target_price_per_unit": Decimal("50"),
                                      "county": "Kiambu", "required_by": date.today() + timedelta(days=10)})
        self.stdout.write(self.style.SUCCESS(
            f"Seeded 1 admin, {len(farmers)} farmers, {len(buyers)} buyers, {len(listings)} listings. "
            f"Log in with admin.demo@example.test / wanjiru.farmer@example.test / achieng.buyer@example.test and password '{pw}'."))
