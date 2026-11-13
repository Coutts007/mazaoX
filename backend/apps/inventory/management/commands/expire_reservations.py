from django.core.management.base import BaseCommand

from apps.inventory import services


class Command(BaseCommand):
    help = "Mark overdue stock reservations as expired (run every minute from cron or a scheduler)."

    def handle(self, *args, **options):
        self.stdout.write(f"Expired {services.expire_reservations()} reservation(s).")
