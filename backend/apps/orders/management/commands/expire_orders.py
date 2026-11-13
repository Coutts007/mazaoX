from django.core.management.base import BaseCommand

from apps.orders import services


class Command(BaseCommand):
    help = "Expire unpaid orders whose payment window has elapsed and release their stock."

    def handle(self, *args, **options):
        self.stdout.write(f"Expired {services.expire_unpaid_orders()} order(s).")
