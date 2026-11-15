from django.core.management.base import BaseCommand

from apps.demand import services


class Command(BaseCommand):
    help = "Mark open demand requests whose required-by date has passed as expired."

    def handle(self, *args, **options):
        self.stdout.write(f"Expired {services.expire_overdue()} demand request(s).")
