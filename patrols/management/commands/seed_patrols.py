from django.core.management.base import BaseCommand
from patrols.models import PatrolUnit


SEED_DATA = [
    {
        "unit_name": "Unit Alpha",
        "status": "available",
        "current_lat": 6.6760,
        "current_lng": -1.5700,
        "area_of_patrol": "Main Campus",
        "shift_start": "18:00",
        "shift_end": "06:00",
    },
    {
        "unit_name": "Unit Beta",
        "status": "available",
        "current_lat": 6.6720,
        "current_lng": -1.5680,
        "area_of_patrol": "Brunei & Hall 7 Area",
        "shift_start": "18:00",
        "shift_end": "06:00",
    },
    {
        "unit_name": "Unit Gamma",
        "status": "available",
        "current_lat": 6.6800,
        "current_lng": -1.5740,
        "area_of_patrol": "Ayeduase & Gaza Area",
        "shift_start": "18:00",
        "shift_end": "06:00",
    },
    {
        "unit_name": "Unit Delta",
        "status": "offline",
        "current_lat": None,
        "current_lng": None,
        "area_of_patrol": "Engineering & KSB Area",
        "shift_start": "06:00",
        "shift_end": "18:00",
    },
]


class Command(BaseCommand):
    help = "Seed the database with patrol units"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing patrol units before seeding",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            deleted, _ = PatrolUnit.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} patrol unit(s)."))

        created = 0
        skipped = 0

        for data in SEED_DATA:
            _, was_created = PatrolUnit.objects.get_or_create(
                unit_name=data["unit_name"],
                defaults=data,
            )
            if was_created:
                created += 1
            else:
                skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done! Created: {created}, Skipped: {skipped}"
            )
        )